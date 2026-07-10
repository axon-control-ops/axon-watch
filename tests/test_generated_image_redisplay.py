from __future__ import annotations

import unittest
from unittest.mock import patch

from app.chat.generated_image_redisplay import (
    build_generated_image_redisplay_reply,
    looks_like_generated_image_redisplay_request,
    maybe_generated_image_redisplay_reply,
)


class GeneratedImageRedisplayTests(unittest.TestCase):
    def test_detector_accepts_show_me_images(self) -> None:
        self.assertTrue(looks_like_generated_image_redisplay_request("show me the images"))
        self.assertTrue(looks_like_generated_image_redisplay_request("open the generated images"))
        self.assertTrue(looks_like_generated_image_redisplay_request("where are the images"))

    def test_detector_rejects_new_generation(self) -> None:
        self.assertFalse(looks_like_generated_image_redisplay_request("generate an image of a cat"))
        self.assertFalse(looks_like_generated_image_redisplay_request("show me an image of a cat"))
        self.assertFalse(looks_like_generated_image_redisplay_request("what is the weather"))

    def test_build_reply_emits_image_blocks(self) -> None:
        reply = build_generated_image_redisplay_reply(
            ["assets/parent-after.png", "assets/principal-after.png"]
        )
        self.assertIn("Here are the generated images", reply)
        self.assertIn(":::image assets/parent-after.png", reply)
        self.assertIn(":::image assets/principal-after.png", reply)

    def test_maybe_reply_requires_thread_paths(self) -> None:
        with patch(
            "app.chat.generated_image_redisplay.chat_store.get_thread",
            return_value={"thread_id": "thread_1"},
        ), patch(
            "app.chat.generated_image_redisplay.collect_thread_generated_image_paths",
            return_value=["assets/mock.png"],
        ):
            reply = maybe_generated_image_redisplay_reply(
                "show me the images",
                workspace_id="workspace_axon_watch",
                thread_id="thread_1",
            )
        self.assertIsNotNone(reply)
        self.assertIn(":::image assets/mock.png", reply or "")

    def test_maybe_reply_returns_none_without_paths(self) -> None:
        with patch(
            "app.chat.generated_image_redisplay.chat_store.get_thread",
            return_value={"thread_id": "thread_1"},
        ), patch(
            "app.chat.generated_image_redisplay.collect_thread_generated_image_paths",
            return_value=[],
        ):
            reply = maybe_generated_image_redisplay_reply(
                "show me the images",
                workspace_id="workspace_axon_watch",
                thread_id="thread_1",
            )
        self.assertIsNone(reply)


if __name__ == "__main__":
    unittest.main()
