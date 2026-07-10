"""Lane B helpers for image attachments and open-file UI actions."""

from __future__ import annotations

from app.chat.generated_image_redisplay import maybe_generated_image_redisplay_reply
from app.chat.lane_b_image_attachments import ingest_agent_generated_images
from app.chat.open_file_intent import open_file_ui_action, resolve_open_file_intent
from app.cli_runtime.generated_image_paths import dedupe_image_paths, image_paths_from_markdown


def generated_image_paths_from_lane_b_result(
    lane_b_result: dict[str, object],
    agent_content: str,
) -> list[str]:
    paths: list[str] = []
    raw_paths = lane_b_result.get("generated_image_paths")
    if isinstance(raw_paths, list):
        paths.extend(str(item).strip() for item in raw_paths if str(item).strip())
    paths.extend(image_paths_from_markdown(agent_content))
    return dedupe_image_paths(paths)


def lane_b_open_file_ui_action(
    *,
    operator_content: str,
    workspace_id: str,
    thread_id: str,
    lane_b_result: dict[str, object] | None = None,
    agent_content: str | None = None,
) -> dict[str, object] | None:
    intent = resolve_open_file_intent(
        operator_content,
        workspace_id=workspace_id,
        thread_id=thread_id,
        lane_b_result=lane_b_result,
        agent_content=agent_content,
    )
    if intent is None:
        return None
    return open_file_ui_action(intent, workspace_id=workspace_id)


def bind_agent_generated_images(
    *,
    workspace_id: str,
    message_id: str,
    thread_id: str,
    lane_b_result: dict[str, object],
    agent_content: str,
    created_at: str,
) -> list[dict[str, object]]:
    image_paths = generated_image_paths_from_lane_b_result(lane_b_result, agent_content)
    return ingest_agent_generated_images(
        workspace_id=workspace_id,
        message_id=message_id,
        thread_id=thread_id,
        image_paths=image_paths,
        created_at=created_at,
    )


__all__ = [
    "bind_agent_generated_images",
    "generated_image_paths_from_lane_b_result",
    "lane_b_open_file_ui_action",
    "maybe_generated_image_redisplay_reply",
]
