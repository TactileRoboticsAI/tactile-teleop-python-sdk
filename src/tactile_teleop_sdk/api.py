import asyncio
import logging

import numpy as np
import requests

from tactile_teleop_sdk.camera.camera_streamer import CameraStreamer
from tactile_teleop_sdk.config import TactileTeleopConfig
from tactile_teleop_sdk.inputs.base import ArmGoal
from tactile_teleop_sdk.inputs.vr_controller import VRController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")


class TactileAPI:
    def __init__(self, api_key: str, robot_name: str):
        self.config = TactileTeleopConfig()
        self.vr_controller = None
        self.camera_streamer = None
        self.api_key = api_key
        self.robot_name = robot_name
        self.backend_url = "https://10.19.20.36:8443"
        self.session_data = None

    async def authenticate(self, participant_identity: str):
        """
        Authenticate robot and get LiveKit session.

        This calls the FastAPI backend which:
        1. Verifies the robot exists in Supabase
        2. Validates the API key hash
        3. Creates a temporary LiveKit session
        4. Returns room name and token for LiveKit connection
        """
        url = f"{self.backend_url}/api/sdk/auth"

        payload = {
            "robot_name": self.robot_name,
            "api_key": self.api_key,
            "participant_identity": participant_identity,
        }

        try:
            response = requests.post(url, json=payload, timeout=10, verify=False)
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.text
                    print(f"Error details: {error_detail}")
                except Exception as e:
                    print(f"Error details: {e}")
            raise

    async def connect_vr_controller(self):
        participant_identity = "controllers-processing"
        livekit_data = await self.authenticate(participant_identity)
        self.vr_controller = VRController()
        await self.vr_controller.start(
            livekit_data["room_name"],
            participant_identity,
            livekit_data["token"],
            livekit_data["livekit_url"],
        )

    async def connect_camera_streamer(self):
        participant_identity = "camera_streamer"
        livekit_data = await self.authenticate(participant_identity)
        self.camera_streamer = CameraStreamer(self.config.camera_config)
        await self.camera_streamer.start(
            livekit_data["room_name"],
            participant_identity,
            livekit_data["token"],
            livekit_data["livekit_url"],
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
