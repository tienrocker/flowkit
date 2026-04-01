"""
WebSocket client to communicate with Google Flow Chrome Extension.
Extension runs as WS server, agent connects as client.
"""
import asyncio
import json
import logging
import uuid
from typing import Optional
import websockets

from agent.config import WS_HOST, WS_PORT

logger = logging.getLogger(__name__)


class FlowClient:
    """Connects to the Chrome extension via WebSocket to call Google Flow APIs."""

    def __init__(self, host: str = WS_HOST, port: int = WS_PORT):
        self.uri = f"ws://{host}:{port}"
        self.ws = None
        self._pending: dict[str, asyncio.Future] = {}

    async def connect(self):
        """Establish WebSocket connection to extension."""
        try:
            self.ws = await websockets.connect(self.uri)
            asyncio.create_task(self._listen())
            logger.info("Connected to extension at %s", self.uri)
        except Exception as e:
            logger.error("Failed to connect to extension: %s", e)
            self.ws = None

    async def _listen(self):
        """Listen for responses from extension."""
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                req_id = msg.get("requestId")
                if req_id and req_id in self._pending:
                    self._pending[req_id].set_result(msg)
        except websockets.ConnectionClosed:
            logger.warning("Extension WebSocket disconnected")
            self.ws = None

    async def _call(self, method: str, params: dict, timeout: float = 300) -> dict:
        """Send a request to extension and wait for response."""
        if not self.ws:
            await self.connect()
        if not self.ws:
            return {"error": "Not connected to extension"}

        req_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        await self.ws.send(json.dumps({
            "requestId": req_id,
            "method": method,
            "params": params,
        }))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"error": f"Timeout waiting for {method}"}
        finally:
            self._pending.pop(req_id, None)

    async def generate_image(self, prompt: str, characters: list[dict],
                              orientation: str = "VERTICAL") -> dict:
        """Generate image for a scene.
        characters: [{"name": "Bijou", "media_gen_id": "..."}]
        Returns: {"mediaGenerationId": "...", "imageUrl": "..."}
        """
        return await self._call("generate_image", {
            "prompt": prompt,
            "characters": characters,
            "orientation": orientation,
        })

    async def generate_video(self, media_gen_id: str, prompt: str,
                              orientation: str = "VERTICAL",
                              end_scene_media_gen_id: str = None,
                              model: str = "veo_3_1_fast") -> dict:
        """Generate video from image mediaGenerationId.
        Returns: {"mediaGenerationId": "...", "videoUrl": "..."}
        """
        params = {
            "mediaGenerationId": media_gen_id,
            "prompt": prompt,
            "orientation": orientation,
            "model": model,
        }
        if end_scene_media_gen_id:
            params["endSceneMediaGenerationId"] = end_scene_media_gen_id
        return await self._call("generate_video", params, timeout=420)

    async def upscale_video(self, media_gen_id: str,
                             orientation: str = "VERTICAL",
                             resolution: str = "VIDEO_RESOLUTION_4K") -> dict:
        """Upscale a video.
        Returns: {"mediaGenerationId": "...", "videoUrl": "..."}
        """
        return await self._call("upscale_video", {
            "mediaGenerationId": media_gen_id,
            "orientation": orientation,
            "resolution": resolution,
        }, timeout=300)

    async def generate_character_image(self, name: str, description: str) -> dict:
        """Generate character reference image.
        Returns: {"mediaGenerationId": "...", "imageUrl": "..."}
        """
        return await self._call("generate_character_image", {
            "name": name,
            "description": description,
        })

    async def get_credits(self) -> dict:
        """Get remaining credits and tier info."""
        return await self._call("get_credits", {}, timeout=10)

    async def close(self):
        if self.ws:
            await self.ws.close()


# Singleton
_client: Optional[FlowClient] = None


def get_flow_client() -> FlowClient:
    global _client
    if _client is None:
        _client = FlowClient()
    return _client
