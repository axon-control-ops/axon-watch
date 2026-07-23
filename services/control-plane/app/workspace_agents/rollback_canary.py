"""Gate 11 — staging deploy, automatic rollback, measured canary gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HUMAN_APPROVAL_ACTIONS = frozenset(
    {
        "merge",
        "production",
        "secrets",
        "destructive_migration",
        "spending",
        "external_communications",
        "authority_expansion",
    }
)


@dataclass
class ReleaseArtifact:
    artifact_id: str
    digest: str
    project_id: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StagingDeployment:
    deployment_id: str
    artifact_id: str
    previous_artifact_id: str | None
    status: str = "deployed"
    smoke_passed: bool | None = None
    rolled_back: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CanaryReport:
    project_class: str
    total: int
    successes: int
    unauthorized_effects: int
    live_tree_corruptions: int
    rollback_drills_passed: int
    rollback_drills_total: int

    @property
    def success_rate(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.successes / self.total

    def meets_thresholds(
        self,
        *,
        min_success_rate: float = 0.90,
        min_tasks: int = 20,
    ) -> bool:
        return (
            self.total >= min_tasks
            and self.success_rate >= min_success_rate
            and self.unauthorized_effects == 0
            and self.live_tree_corruptions == 0
            and self.rollback_drills_total > 0
            and self.rollback_drills_passed == self.rollback_drills_total
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success_rate"] = self.success_rate
        payload["meets_thresholds"] = self.meets_thresholds()
        return payload


class StagingController:
    def __init__(self) -> None:
        self._artifacts: dict[str, ReleaseArtifact] = {}
        self._deployments: dict[str, StagingDeployment] = {}
        self._active_by_project: dict[str, str] = {}

    def register_artifact(self, artifact: ReleaseArtifact) -> ReleaseArtifact:
        if not artifact.immutable:
            raise ValueError("staging artifacts must be immutable")
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def deploy(
        self,
        *,
        deployment_id: str,
        project_id: str,
        artifact_id: str,
    ) -> StagingDeployment:
        if artifact_id not in self._artifacts:
            raise KeyError(f"unknown artifact: {artifact_id}")
        previous = self._active_by_project.get(project_id)
        dep = StagingDeployment(
            deployment_id=deployment_id,
            artifact_id=artifact_id,
            previous_artifact_id=previous,
            status="deployed",
        )
        self._deployments[deployment_id] = dep
        self._active_by_project[project_id] = artifact_id
        return dep

    def run_smoke(self, deployment_id: str, *, passed: bool) -> StagingDeployment:
        dep = self._deployments[deployment_id]
        dep.smoke_passed = passed
        if not passed:
            self.rollback(deployment_id)
        else:
            dep.status = "healthy"
        return dep

    def rollback(self, deployment_id: str) -> StagingDeployment:
        dep = self._deployments[deployment_id]
        artifact = self._artifacts[dep.artifact_id]
        previous = dep.previous_artifact_id
        if previous:
            self._active_by_project[artifact.project_id] = previous
        dep.rolled_back = True
        dep.status = "rolled_back"
        return dep


def requires_human_approval(action: str) -> bool:
    return str(action or "").strip().lower() in HUMAN_APPROVAL_ACTIONS


def evaluate_canary(
    *,
    project_class: str,
    outcomes: list[dict[str, Any]],
    rollback_drills: list[bool],
) -> CanaryReport:
    successes = sum(1 for item in outcomes if item.get("success"))
    unauthorized = sum(1 for item in outcomes if item.get("unauthorized_effect"))
    corruptions = sum(1 for item in outcomes if item.get("live_tree_corruption"))
    return CanaryReport(
        project_class=project_class,
        total=len(outcomes),
        successes=successes,
        unauthorized_effects=unauthorized,
        live_tree_corruptions=corruptions,
        rollback_drills_passed=sum(1 for ok in rollback_drills if ok),
        rollback_drills_total=len(rollback_drills),
    )
