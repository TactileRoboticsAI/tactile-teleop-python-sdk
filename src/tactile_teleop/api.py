import asyncio
import logging

import numpy as np

from tactile_teleop.camera.camera_streamer import CameraStreamer
from tactile_teleop.config import TactileTeleopConfig
from tactile_teleop.inputs.vr_controller import VRController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")


class API:
    def __init__(self):
        self.config = TactileTeleopConfig()
        self.vr_controller = VRController()
        self.camera_streamer = CameraStreamer(self.config.camera_config)

    async def start_vr_controller(self):
        await self.vr_controller.start(self.config.livekit_room, self.config.controllers_processing_participant)

    async def start_camera_streamer(self):
        await self.camera_streamer.start(self.config.livekit_room, self.config.camera_streamer_participant)

    async def stop_vr_controller(self):
        await self.vr_controller.stop()

    async def stop_camera_streamer(self):
        await self.camera_streamer.stop()

    async def send_stereo_frame(self, frame: np.ndarray):
        await self.camera_streamer.send_stereo_frame(frame)
        await asyncio.sleep(0.001)

    async def send_single_frame(self, frame: np.ndarray):
        await self.camera_streamer.send_single_frame(frame)

    async def get_controller_goal(self, arm: str):
        await asyncio.sleep(0.001)
        return await self.vr_controller.get_controller_goal(arm)
