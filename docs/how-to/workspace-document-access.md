# Workspace document access (PDFs, RFQs, deliverables)

Fleet agents work inside a **disposable git checkout** of the bound project root. By default that checkout only contains **committed** files. Document workflows also need **live** PDFs, filled forms, and generated output that may exist only on disk.

## What is enabled

| Capability | Mechanism |
|---|---|
| Read uncommitted PDFs/docs | `ensure_document_assets_borrowed()` copies `docs/`, `output/`, `assets/`, `data/`, `website/` from bound root → isolation checkout at worker start |
| Run fill scripts | Approved prefix `python3 scripts/…` (repo-local scripts only) |
| Inspect PDFs | Approved prefixes `pdftotext`, `pdftoppm` |
| Write deliverables | Frontend/Lead roles + task `allowed_paths` intersect contract paths (`docs/`, `output/`, `assets/`, `scripts/`, `website/`) |
| Smart-routing on blocks | Document goals route to Frontend with document paths, not only `services/ops` |

## Host prerequisites

```bash
./scripts/ops/install-agent-sandbox-host-deps.sh   # python3 + poppler-utils (pdftotext)
./scripts/ops/provision-all-workspace-runtimes.sh  # npm + project.axon.yaml per binding
```

## Per-workspace setup

1. Ensure `config/workspace-project-bindings.json` maps the workspace → on-disk repo (e.g. `workspace_tps` → TPS client root).
2. Put fill scripts under `scripts/` in that repo (e.g. `scripts/fill-rfq26052-pdf.py`).
3. For Python PDF deps (PyMuPDF, etc.), use a workspace `.venv` and run `.venv/bin/python3 scripts/…`.
4. Lease tasks with `allowed_paths` including document dirs when assigning PDF/RFQ work.
5. **Commit reference PDFs** when they must appear in git history; borrow covers uncommitted operator edits until commit.

## Operator vs agent surfaces

| Surface | Sees live bound root? |
|---|---|
| Monaco / workspace file API | Yes (includes uncommitted) |
| Lane B worker isolation | Committed snapshot + borrowed document trees |
| Agent terminal (scoped) | Bound root cwd; commands still pass shell hook |

## Limits (by design)

- Agents cannot read paths **outside** their workspace binding (no cross-repo host browse).
- `python3` only runs for `scripts/<file>` under the checkout — not arbitrary `-c` or absolute paths.
- Secrets (`.env`, `secrets/`) stay forbidden per `project.axon.yaml`.
