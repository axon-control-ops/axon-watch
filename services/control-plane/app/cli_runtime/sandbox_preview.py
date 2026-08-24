"""Run a workspace's dev server against the composer Sandbox checkout.

Review/Preview could previously only *describe* the change (changed paths plus
a copy-paste hint). This lane actually starts the workspace's preview command
inside the sandbox checkout on a spare port, so the operator can look at the
change running before anything is published to the bound project root.

The job is an Axon-owned PTY job on the sandbox terminal lane, so it is visible,
streamable and cancellable like any other terminal job — and, being operator
initiated, it does not require widening the agent shell allowlist.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
from pathlib import Path
from typing import Any

from app.terminal.agent_jobs import (
    TARGET_SANDBOX,
    cancel_agent_terminal_job,
    enqueue_agent_terminal_job,
    get_agent_terminal_job,
)
from app.terminal.agent_job_registry import TERMINAL_STATUSES

# 8082 is conventionally the bound/root workspace preview; sandbox previews take
# the range above it so the two can run side by side and be compared.
PREVIEW_PORT_RANGE = range(8083, 8100)

_LOCK = threading.RLock()
_ACTIVE: dict[str, dict[str, Any]] = {}


class SandboxPreviewError(RuntimeError):
    """The sandbox preview could not be started for this workspace."""


class MissingToolchainError(SandboxPreviewError):
    """Nothing to borrow: neither side has installed dependencies.

    Fatal for a preview (a dev server cannot start without them) but merely
    informational when preparing an isolation checkout — a docs or SQL task
    needs no node_modules, and failing the whole run over it killed dispatches
    on workspaces that simply have not been installed.
    """


def _port_is_free(port: int) -> bool:
    """Probe a loopback bind. Inherently racy — the dev server binds moments
    later — but it is enough to skip ports already held by another preview."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _allocate_port() -> int:
    for port in PREVIEW_PORT_RANGE:
        if _port_is_free(port):
            return port
    raise SandboxPreviewError(
        f"no free preview port in {PREVIEW_PORT_RANGE.start}-{PREVIEW_PORT_RANGE.stop - 1}"
    )


def _directory_is_populated(path: Path) -> bool:
    try:
        return path.is_dir() and any(path.iterdir())
    except OSError:
        return False


def ensure_preview_dependencies(checkout: Path, bound_root: Path) -> str:
    """Make the checkout runnable by borrowing the bound root's ``node_modules``.

    The sandbox checkout is a git worktree (or shallow clone), so it contains
    only tracked files — ``node_modules`` is gitignored and therefore absent or
    empty. Without this the preview command always dies instantly on a missing
    binary, which is precisely how this lane failed the first time it ran.

    ``node_modules`` itself is a **real directory** holding one symlink per
    package, rather than a single symlink to the bound root's tree. That
    distinction is load-bearing, not cosmetic:

    * ``node_modules`` is an approved writable root for some roles. The agent
      sandbox rejects any writable root that resolves outside the disposable
      workspace — correctly, since granting write through an escaping link
      would let a sandboxed agent mutate the bound project. Linking the whole
      directory therefore failed every Lane B dispatch outright.
    * A real directory resolves inside the workspace, so the guard is satisfied
      untouched, and anything an agent creates lands in the checkout rather
      than in the bound project.

    Per-package links rather than a copy because the tree here is ~2GB across
    ~108k files, and ``/tmp`` is a different filesystem from the project, so
    hardlinking (``cp -al``) is not available either.
    """
    target = checkout / "node_modules"
    source = bound_root / "node_modules"
    if not _directory_is_populated(source):
        raise MissingToolchainError(
            f"neither the sandbox checkout nor {bound_root} has installed "
            "dependencies, so there is nothing to preview — run an install in "
            "the bound workspace first"
        )

    # A stale whole-tree symlink from an earlier build of this lane must go.
    if target.is_symlink():
        target.unlink()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SandboxPreviewError(f"could not create {target}: {exc}") from exc

    linked = 0
    bin_links = 0
    for entry in source.iterdir():
        destination = target / entry.name
        if entry.name == ".bin" and entry.is_dir():
            try:
                bin_links += _link_bin_directory(entry, destination)
            except OSError:
                pass
            continue
        if destination.exists() or destination.is_symlink():
            continue
        try:
            destination.symlink_to(entry, target_is_directory=entry.is_dir())
            linked += 1
        except OSError:
            continue
    if not any(
        (target / entry.name).exists() or (target / entry.name).is_symlink()
        for entry in source.iterdir()
    ):
        raise SandboxPreviewError(f"could not link any dependencies into {target}")
    workspace_bin_links = _link_workspace_bin_shims(checkout)
    if linked == 0 and bin_links == 0 and workspace_bin_links == 0:
        return "checkout already has dependencies"
    notes = [f"linked {linked} packages into {target}"]
    if bin_links:
        notes.append(f"{bin_links} root bin shims")
    if workspace_bin_links:
        notes.append(f"{workspace_bin_links} workspace bin shims")
    return "; ".join(notes)


def _link_bin_directory(source_bin: Path, target_bin: Path) -> int:
    """Create a real checkout-local .bin dir instead of an escaping dir symlink."""
    if target_bin.is_symlink():
        target_bin.unlink()
    target_bin.mkdir(parents=True, exist_ok=True)
    linked = 0
    for source in source_bin.iterdir():
        destination = target_bin / source.name
        if destination.exists() or destination.is_symlink():
            continue
        try:
            if source.is_symlink():
                destination.symlink_to(os.readlink(source))
            else:
                destination.symlink_to(source, target_is_directory=source.is_dir())
            linked += 1
        except OSError:
            continue
    return linked


def _workspace_package_roots(root: Path) -> list[Path]:
    package_json = root / "package.json"
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = package.get("workspaces") if isinstance(package, dict) else None
    patterns: list[str] = []
    if isinstance(raw, list):
        patterns = [str(item) for item in raw if isinstance(item, str)]
    elif isinstance(raw, dict) and isinstance(raw.get("packages"), list):
        patterns = [str(item) for item in raw["packages"] if isinstance(item, str)]
    roots: list[Path] = []
    for pattern in patterns:
        if pattern.startswith("!") or ".." in Path(pattern).parts:
            continue
        for candidate in root.glob(pattern):
            if (candidate / "package.json").is_file():
                roots.append(candidate)
    return sorted(set(roots))


def _link_workspace_bin_shims(root: Path) -> int:
    root_bin = root / "node_modules" / ".bin"
    if not root_bin.is_dir():
        return 0
    linked = 0
    for workspace_root in _workspace_package_roots(root):
        bin_dir = workspace_root / "node_modules" / ".bin"
        if bin_dir.is_symlink():
            continue
        try:
            bin_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        for source in root_bin.iterdir():
            destination = bin_dir / source.name
            if destination.exists() or destination.is_symlink():
                continue
            try:
                relative = os.path.relpath(source, bin_dir)
                destination.symlink_to(relative, target_is_directory=source.is_dir())
                linked += 1
            except OSError:
                continue
    return linked


# Git worktrees omit untracked deliverables (PDFs, filled forms, generated output).
# Borrow live copies from the bound project root so agents can read/edit documents
# the operator created locally without committing first.
_DOCUMENT_BORROW_ROOTS: tuple[str, ...] = (
    "docs",
    "output",
    "assets",
    "data",
    "website/documents",
    "website",
)


def _should_copy_borrowed_file(source: Path, target: Path) -> bool:
    if not source.is_file():
        return False
    if not target.exists():
        return True
    try:
        return source.stat().st_mtime > target.stat().st_mtime
    except OSError:
        return False


def ensure_document_assets_borrowed(checkout: Path, bound_root: Path) -> list[str]:
    """Copy untracked or newer document trees from bound root into an isolation checkout."""
    copied: list[str] = []
    if not bound_root.is_dir():
        return copied

    for relative in _DOCUMENT_BORROW_ROOTS:
        source_root = bound_root / relative
        if not source_root.is_dir():
            continue
        for source in source_root.rglob("*"):
            if not source.is_file():
                continue
            name = source.name
            if name.startswith(".env"):
                continue
            try:
                rel = source.relative_to(bound_root)
            except ValueError:
                continue
            target = checkout / rel
            if not _should_copy_borrowed_file(source, target):
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target, follow_symlinks=True)
                copied.append(rel.as_posix())
            except OSError:
                continue
    return copied


def ensure_checkout_python_venv(checkout: Path, bound_root: Path) -> str | None:
    """Create a local .venv in the checkout when requirements.txt needs PyMuPDF etc.

    Worktrees omit gitignored ``.venv``; agents run ``.venv/bin/python3 scripts/…``.
    Provisioning runs on the host during isolation materialization (outside bwrap).
    """
    req = checkout / "requirements.txt"
    if not req.is_file():
        bound_req = bound_root / "requirements.txt"
        if bound_req.is_file():
            try:
                shutil.copy2(bound_req, req, follow_symlinks=True)
            except OSError:
                return None
        else:
            return None
    python_bin = checkout / ".venv" / "bin" / "python3"
    if python_bin.is_file():
        return "checkout python venv already present"
    try:
        subprocess.run(
            ["python3", "-m", "venv", str(checkout / ".venv")],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"python venv create failed: {exc}"
    pip = checkout / ".venv" / "bin" / "pip"
    if not pip.is_file():
        return "python venv missing pip"
    try:
        completed = subprocess.run(
            [str(pip), "install", "-r", str(req)],
            cwd=checkout,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return f"python venv pip install failed: {exc}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "pip install failed")[:200]
        return f"python venv pip install failed: {detail}"
    return f"installed python venv from {req.name}"


def ensure_preview_env_files(checkout: Path, bound_root: Path) -> list[str]:
    """Copy the bound root's local env files into the checkout.

    Same root cause as the missing dependencies: ``.env`` / ``.env.local`` are
    gitignored, so a worktree only ever receives the tracked ``.env.example``.
    The app then boots into the checkout and dies on unset configuration, which
    reads as a broken preview when it is really a missing-config artifact of
    isolation.

    Real files, not symlinks: bubblewrap cannot ro-bind over escaping file
    symlinks (``Can't create file at …/.env.production``), which blocked every
    Cursor dispatch once env borrows were linked. Copies stay in the disposable
    checkout under ``/tmp`` and are removed with the sandbox; they are not
    written back to the bound project root.
    """
    linked: list[str] = []
    if not bound_root.is_dir():
        return linked
    for source in sorted(bound_root.glob(".env*")):
        if not source.is_file():
            continue
        # .env.example is tracked and already present; never shadow it.
        if source.name == ".env.example":
            continue
        target = checkout / source.name
        if target.is_symlink():
            try:
                target.unlink()
            except OSError:
                continue
        if target.exists():
            continue
        try:
            shutil.copy2(source, target, follow_symlinks=True)
            linked.append(source.name)
        except OSError:
            # A preview without one env file is still worth starting; the app
            # will say which variable it needs.
            continue
    return linked


def _materialize_borrowed_env_symlinks(checkout: Path, bound_root: Path) -> list[str]:
    """Replace stale escaping env symlinks with real copies for bwrap compatibility."""
    repaired: list[str] = []
    if not bound_root.is_dir():
        return repaired
    for target in checkout.glob(".env*"):
        if target.name == ".env.example":
            continue
        if not target.is_symlink():
            continue
        source = bound_root / target.name
        if not source.is_file():
            try:
                target.unlink()
                repaired.append(target.name)
            except OSError:
                pass
            continue
        try:
            target.unlink()
            shutil.copy2(source, target, follow_symlinks=True)
            repaired.append(target.name)
        except OSError:
            continue
    return repaired


def ensure_sandbox_checkout_runnable(checkout: Path, bound_root: Path) -> dict[str, Any]:
    """Borrow runnable toolchain artifacts from the bound workspace into a disposable checkout.

    Preview already did this on start; agents and terminal jobs need the same borrow
    at materialization time so ``npx --no-install jest`` and dev scripts work without
    asking the operator to start Preview first.
    """
    notes: list[str] = []
    errors: list[str] = []
    try:
        notes.append(ensure_preview_dependencies(checkout, bound_root))
    except MissingToolchainError as exc:
        # Nothing to borrow is not a failure to prepare a checkout. Raising here
        # aborted worker isolation entirely for workspaces with no node_modules.
        notes.append(f"no toolchain to borrow: {exc}")
    except SandboxPreviewError as exc:
        errors.append(str(exc))
    try:
        linked_env = ensure_preview_env_files(checkout, bound_root)
        if linked_env:
            notes.append(f"copied env files: {', '.join(linked_env)}")
        repaired_env = _materialize_borrowed_env_symlinks(checkout, bound_root)
        if repaired_env:
            notes.append(f"repaired env symlinks: {', '.join(repaired_env)}")
    except OSError as exc:
        errors.append(f"could not link env files: {exc}")
    try:
        borrowed_docs = ensure_document_assets_borrowed(checkout, bound_root)
        if borrowed_docs:
            sample = ", ".join(borrowed_docs[:5])
            suffix = f" (+{len(borrowed_docs) - 5} more)" if len(borrowed_docs) > 5 else ""
            notes.append(f"borrowed document assets: {sample}{suffix}")
    except OSError as exc:
        errors.append(f"could not borrow document assets: {exc}")
    try:
        venv_note = ensure_checkout_python_venv(checkout, bound_root)
        if venv_note:
            notes.append(venv_note)
    except OSError as exc:
        errors.append(f"could not prepare python venv: {exc}")
    return {"ok": not errors, "notes": notes, "errors": errors}


def ensure_isolation_checkout_runnable(checkout: Path) -> dict[str, Any]:
    """Link dependencies/env for an isolation checkout using its sidecar metadata."""
    from app.safe_improvement.isolated_executor import read_baseline_metadata

    try:
        meta = read_baseline_metadata(checkout)
    except Exception as exc:
        return {"ok": False, "notes": [], "errors": [f"missing isolation metadata: {exc}"]}
    bound_raw = str(meta.get("bound_project_root") or "").strip()
    if not bound_raw:
        return {"ok": False, "notes": [], "errors": ["isolation metadata has no bound_project_root"]}
    bound = Path(bound_raw).expanduser().resolve()
    if not bound.is_dir():
        return {
            "ok": False,
            "notes": [],
            "errors": [f"bound project root is missing or not a directory: {bound}"],
        }
    return ensure_sandbox_checkout_runnable(checkout, bound)


def _scripts_and_dependencies(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    package_json = root / "package.json"
    if not package_json.is_file():
        return {}, {}
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, {}
    if not isinstance(package, dict):
        return {}, {}
    scripts = package.get("scripts")
    dependencies = {
        **(package.get("dependencies") if isinstance(package.get("dependencies"), dict) else {}),
        **(
            package.get("devDependencies")
            if isinstance(package.get("devDependencies"), dict)
            else {}
        ),
    }
    return (scripts if isinstance(scripts, dict) else {}), dependencies


# Dev servers that take `--port` as a forwarded CLI argument. Everything else
# only reliably honours the PORT environment variable, and forwarding an
# unknown `--port` to, say, a shell script entrypoint would just crash it.
_PORT_FLAG_DEV_SERVERS = ("vite", "next", "nuxt", "astro")


def sandbox_preview_command(root: Path, port: int) -> str:
    """Best-effort preview command for a checkout, already scoped to ``port``.

    Best-effort is the honest description: the port is applied the way the
    detected dev server actually accepts it, but a project with an unusual
    entrypoint may still ignore it. Callers can pass an explicit command
    instead of relying on this.

    No ``cd`` prefix: the PTY job is spawned with the checkout as its cwd, and a
    ``cd`` would be both redundant and a second place for the path to drift.
    """
    scripts, dependencies = _scripts_and_dependencies(root)
    if "web:dev" in scripts and "expo" in dependencies:
        # Not `npx --no-install expo`: npx resolves the *package*, and in a
        # worktree whose node_modules is borrowed it reports the package as
        # missing and cancels. The local bin shim is what actually exists.
        # --clear is not optional here. Metro caches transformed modules and
        # inlines EXPO_PUBLIC_* at transform time. A fresh checkout's very first
        # preview necessarily runs before/while env files are linked in, which
        # bakes `process.env.X` into the cache as literal `undefined`. The cache
        # is keyed by file content, so restarting never invalidates it and the
        # app reports its config as missing forever. A slower first build is the
        # correct trade for a preview that is not silently wrong.
        local_expo = root / "node_modules" / ".bin" / "expo"
        if local_expo.exists():
            return f"./node_modules/.bin/expo start --web --port {port} --clear"
        return f"npx --no-install expo start --web --port {port} --clear"
    if "dev" in scripts:
        script = str(scripts.get("dev") or "")
        # Prefer the script body, then the dependency list, before deciding the
        # flag is safe to forward.
        forwards_port = any(
            name in script or name in dependencies for name in _PORT_FLAG_DEV_SERVERS
        )
        return (
            f"npm run dev -- --port {port}" if forwards_port else f"PORT={port} npm run dev"
        )
    if "start" in scripts:
        return f"PORT={port} npm start"
    raise SandboxPreviewError(
        "no preview script found in the sandbox checkout (expected a 'dev', "
        "'start' or 'web:dev' entry in package.json). Pass an explicit command "
        "to preview this workspace."
    )


def _live_record(workspace_id: str) -> dict[str, Any] | None:
    """Return the tracked preview, dropping it once its job has terminated."""
    entry = _ACTIVE.get(workspace_id)
    if entry is None:
        return None
    job = get_agent_terminal_job(str(entry.get("job_id") or ""))
    if job is None or str(job.get("status") or "") in TERMINAL_STATUSES:
        _ACTIVE.pop(workspace_id, None)
        return None
    return {**entry, "job": job}


def sandbox_preview_status(workspace_id: str) -> dict[str, Any]:
    clean = str(workspace_id or "").strip()
    with _LOCK:
        entry = _live_record(clean)
    if entry is None:
        return {"workspace_id": clean, "running": False}
    return {"workspace_id": clean, "running": True, **entry}


def start_sandbox_preview(
    workspace_id: str, *, command: str | None = None, port: int | None = None
) -> dict[str, Any]:
    """Start (or return the already-running) sandbox preview for a workspace.

    ``command``/``port`` let an operator override the heuristic for a project
    whose entrypoint it cannot infer.
    """
    clean = str(workspace_id or "").strip()
    if not clean:
        raise SandboxPreviewError("workspace_id is required")
    if port is not None and port not in PREVIEW_PORT_RANGE:
        raise SandboxPreviewError(
            f"preview port must be within {PREVIEW_PORT_RANGE.start}-"
            f"{PREVIEW_PORT_RANGE.stop - 1}"
        )

    from app.cli_runtime.composer_sandbox import resolve_sandbox_workspace_root

    with _LOCK:
        existing = _live_record(clean)
        if existing is not None:
            return {"workspace_id": clean, "running": True, "reused": True, **existing}

        root = resolve_sandbox_workspace_root(clean)
        if root is None:
            raise SandboxPreviewError(
                "sandbox is not enabled for this workspace, so there is no "
                "checkout to preview"
            )

        # Dependencies must be linked before the command is derived: the expo
        # branch probes node_modules/.bin to choose its invocation.
        from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

        try:
            bound_root = resolve_workspace_root(clean)
        except WorkspaceRootError as exc:
            raise SandboxPreviewError(str(exc)) from exc
        dependency_note = ensure_preview_dependencies(root, bound_root)
        env_files = ensure_preview_env_files(root, bound_root)

        resolved_port = port if port is not None else _allocate_port()
        resolved_command = str(command or "").strip() or sandbox_preview_command(
            root, resolved_port
        )
        # service=True: a dev server never exiting is success, so it must not
        # inherit the batch job cap that would reap it mid-review.
        job = enqueue_agent_terminal_job(
            workspace_id=clean,
            command=resolved_command,
            stream_to_chat=False,
            target=TARGET_SANDBOX,
            service=True,
        )
        entry = {
            "job_id": str(job.get("job_id") or ""),
            "port": resolved_port,
            "url": f"http://localhost:{resolved_port}",
            "command": resolved_command,
            "checkout_root": str(root),
            "timeout_seconds": job.get("timeout_seconds"),
            "dependencies": dependency_note,
            "env_files": env_files,
        }
        _ACTIVE[clean] = entry
        return {"workspace_id": clean, "running": True, "reused": False, "job": job, **entry}


def remove_preview_bootstrap_links(checkout: Path) -> list[str]:
    """Drop the borrowed links once a preview is done with them.

    They are only safe while read-only, and every extra minute they exist is a
    minute an agent dispatch has to reason about a checkout that reaches
    outside itself. Only symlinks are removed — never real content.
    """
    import shutil

    removed: list[str] = []
    modules = checkout / "node_modules"
    try:
        if modules.is_symlink():
            modules.unlink()
            removed.append("node_modules")
        elif modules.is_dir() and all(child.is_symlink() for child in modules.iterdir()):
            # Only tear down a tree we built: every child being a link is the
            # signature of the borrowed layout. A real install stays.
            shutil.rmtree(modules)
            removed.append("node_modules")
    except OSError:
        pass
    for path in checkout.glob(".env*"):
        try:
            if path.is_symlink():
                path.unlink()
                removed.append(path.name)
        except OSError:
            continue
    return removed


def stop_sandbox_preview(workspace_id: str) -> dict[str, Any]:
    clean = str(workspace_id or "").strip()
    with _LOCK:
        entry = _live_record(clean)
        _ACTIVE.pop(clean, None)
    if entry is None:
        return {"workspace_id": clean, "running": False, "stopped": False}
    cancel_agent_terminal_job(str(entry.get("job_id") or ""))
    checkout = str(entry.get("checkout_root") or "").strip()
    removed = remove_preview_bootstrap_links(Path(checkout)) if checkout else []
    return {
        "workspace_id": clean,
        "running": False,
        "stopped": True,
        "port": entry.get("port"),
        "removed_links": removed,
    }


def _listening_processes() -> dict[int, tuple[int, str]]:
    """Map preview-range port -> (pid, process name) for local listeners.

    Uses ``ss`` because it reports the owning pid for the current user without
    elevation. Any failure yields an empty map: the listing degrades to
    "nothing discovered" rather than breaking the panel.
    """
    try:
        result = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}

    found: dict[int, tuple[int, str]] = {}
    for line in (result.stdout or "").splitlines():
        match = re.search(r":(\d+)\s", line)
        if not match:
            continue
        port = int(match.group(1))
        if port not in PREVIEW_PORT_RANGE:
            continue
        owner = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        if owner:
            found[port] = (int(owner.group(2)), owner.group(1))
    return found


def discover_previews(workspace_id: str) -> dict[str, Any]:
    """Every listener on the preview port range, managed or not.

    Orphans matter: a control-plane restart drops the in-memory registry while
    the dev server keeps holding its port, and until now nothing in the product
    could show or reclaim it.
    """
    clean = str(workspace_id or "").strip()
    with _LOCK:
        tracked = _live_record(clean)
    tracked_port = int(tracked.get("port") or 0) if tracked else 0

    items: list[dict[str, Any]] = []
    for port, (pid, process_name) in sorted(_listening_processes().items()):
        managed = port == tracked_port
        items.append(
            {
                "port": port,
                "url": f"http://localhost:{port}",
                "pid": pid,
                "process": process_name,
                "managed": managed,
                "job_id": str(tracked.get("job_id") or "") if managed and tracked else "",
                "command": str(tracked.get("command") or "") if managed and tracked else "",
                "checkout_root": str(tracked.get("checkout_root") or "") if managed and tracked else "",
            }
        )
    return {"workspace_id": clean, "items": items, "count": len(items)}


def stop_preview_port(workspace_id: str, port: int) -> dict[str, Any]:
    """Stop whatever holds a preview port, managed or orphaned.

    Refuses any port outside ``PREVIEW_PORT_RANGE`` so this can never become a
    general-purpose process killer reachable over HTTP.
    """
    clean = str(workspace_id or "").strip()
    if port not in PREVIEW_PORT_RANGE:
        raise SandboxPreviewError(
            f"refusing to stop port {port}: outside the preview range "
            f"{PREVIEW_PORT_RANGE.start}-{PREVIEW_PORT_RANGE.stop - 1}"
        )

    with _LOCK:
        tracked = _live_record(clean)
        if tracked is not None and int(tracked.get("port") or 0) == port:
            _ACTIVE.pop(clean, None)
            cancel_agent_terminal_job(str(tracked.get("job_id") or ""))

    listener = _listening_processes().get(port)
    if listener is None:
        return {"workspace_id": clean, "port": port, "stopped": False, "detail": "nothing was listening"}

    pid, process_name = listener
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise SandboxPreviewError(f"could not stop pid {pid} on port {port}: {exc}") from exc
    return {
        "workspace_id": clean,
        "port": port,
        "stopped": True,
        "pid": pid,
        "process": process_name,
    }


def reset_sandbox_previews() -> None:
    with _LOCK:
        _ACTIVE.clear()


__all__ = [
    "PREVIEW_PORT_RANGE",
    "MissingToolchainError",
    "SandboxPreviewError",
    "discover_previews",
    "reset_sandbox_previews",
    "stop_preview_port",
    "ensure_preview_dependencies",
    "ensure_preview_env_files",
    "ensure_checkout_python_venv",
    "ensure_document_assets_borrowed",
    "ensure_isolation_checkout_runnable",
    "ensure_sandbox_checkout_runnable",
    "remove_preview_bootstrap_links",
    "sandbox_preview_command",
    "sandbox_preview_status",
    "start_sandbox_preview",
    "stop_sandbox_preview",
]
