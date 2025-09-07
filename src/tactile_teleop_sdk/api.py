import asyncio
import logging

import numpy as np

from tactile_teleop_sdk.camera.camera_streamer import CameraStreamer
from tactile_teleop_sdk.config import TactileTeleopConfig
from tactile_teleop_sdk.inputs.base import ArmGoal
from tactile_teleop_sdk.inputs.vr_controller import VRController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")


class TactileAPI:
    def __init__(self):
        self.config = TactileTeleopConfig()
        self.vr_controller = None
        self.camera_streamer = None

    async def connect_vr_controller(self):
        
        self.vr_controller = VRController()
        await self.vr_controller.start(
            self.config.livekit_room,
            self.config.controllers_processing_participant,
            self.config.livekit_token,
            self.config.livekit_url,
        )

    async def connect_camera_streamer(self):
        self.camera_streamer = CameraStreamer(self.config.camera_config)
        await self.camera_streamer.start(
            self.config.livekit_room,
            self.config.camera_streamer_participant,
            self.config.livekit_token,
            self.config.livekit_url,
        )

    async def disconnect_vr_controller(self):
        if not self.vr_controller:
            return
        await self.vr_controller.stop()

    async def disconnect_camera_streamer(self):
        if not self.camera_streamer:
            return
        await self.camera_streamer.stop()

    async def send_stereo_frame(self, frame: np.ndarray):
        if not self.camera_streamer:
            raise ValueError("Camera streamer not connected")
        await self.camera_streamer.send_stereo_frame(frame)
        await asyncio.sleep(0.001)

    async def send_single_frame(self, frame: np.ndarray):
        if not self.camera_streamer:
            raise ValueError("Camera streamer not connected")
        await self.camera_streamer.send_single_frame(frame)

    async def get_controller_goal(self, arm: str) -> ArmGoal:
        if not self.vr_controller:
            raise ValueError("VR controller not connected")
        await asyncio.sleep(0.001)
        return self.vr_controller.get_controller_goal(arm)
