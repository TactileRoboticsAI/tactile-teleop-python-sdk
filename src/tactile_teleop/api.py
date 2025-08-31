import asyncio

import numpy as np

from tactile_teleop.camera.camera_streamer import CameraStreamer
from tactile_teleop.config import TactileTeleopConfig
from tactile_teleop.inputs.vr_controller import VRController


class API:
    def __init__(self):
        self.config = TactileTeleopConfig()
        self.vr_controller = VRController()
        self.camera_streamer = CameraStreamer(self.config.camera_config["dual_camera_opencv"])

    async def start(self):
        await self.vr_controller.start(self.config.livekit_room, self.config.controllers_processing_participant)
        # await self.camera_streamer.start(self.config.livekit_room, self.config.camera_streamer_participant)

    async def stop(self):
        await self.vr_controller.stop()
        await self.camera_streamer.stop()

    async def send_frame(self, frame: np.ndarray):
        await self.camera_streamer.send_frame(frame)

    async def get_controller_goal(self, arm: str):
        # Yield control back to the event loop to get new goals
        await asyncio.sleep(0.001)
        # Process new goals
        return self.vr_controller.get_controller_goal(arm)
