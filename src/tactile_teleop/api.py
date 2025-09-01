import asyncio
import logging

import numpy as np

from tactile_teleop.camera.camera_streamer import CameraStreamer
from tactile_teleop.config import TactileTeleopConfig
from tactile_teleop.inputs.base import ArmGoal
from tactile_teleop.inputs.vr_controller import VRController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")


class TactileAPI:
    def __init__(self):
        self.config = TactileTeleopConfig()

    async def connect_vr_controller(self):
        self.vr_controller = VRController()
        await self.vr_controller.start(self.config.livekit_room, self.config.controllers_processing_participant)

    async def connect_camera_streamer(self):
        self.camera_streamer = CameraStreamer(self.config.camera_config)
        await self.camera_streamer.start(self.config.livekit_room, self.config.camera_streamer_participant)

    async def disconnect_vr_controller(self):
        await self.vr_controller.stop()

    async def disconnect_camera_streamer(self):
        await self.camera_streamer.stop()

    async def send_stereo_frame(self, frame: np.ndarray):
        await self.camera_streamer.send_stereo_frame(frame)
        await asyncio.sleep(0.001)

    async def send_single_frame(self, frame: np.ndarray):
        await self.camera_streamer.send_single_frame(frame)

    async def get_controller_goal(self, arm: str) -> ArmGoal:
        await asyncio.sleep(0.001)
        return self.vr_controller.get_controller_goal(arm)
