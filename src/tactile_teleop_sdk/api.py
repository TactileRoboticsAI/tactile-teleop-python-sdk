import asyncio
import logging

import numpy as np
import requests
from pydantic import BaseModel
from typing import Literal

from tactile_teleop_sdk.camera.livekit_camera_streamer import LivekitCameraStreamer
from tactile_teleop_sdk.config import TeleopConfig
from tactile_teleop_sdk.inputs.base import ArmGoal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")


class AuthNodeResponse(BaseModel):
    room_name: str
    token: str
    protocol_server_url: str
    expires_at: str

class TeleopAPI:
    def __init__(self, config: TeleopConfig):
        """
        Initialize the TactileAPI
        
        Args:
            config (TeleopConfig): The configuration for the teleoperation.
        """
        self.config = config
        self.operator_connected = False
        
        
    async def _auth_node(self, node_id: str, node_role: Literal["subscriber", "publisher"]) -> AuthNodeResponse:
        """
        Authenticate Robot Node and get Protocol Authentication Token.
        """
        url = f"{self.config.backend_url}{self.config.auth_endpoint}"

        payload = {
            "api_key": self.config.api_key,
            "protocol": self.config.protocol,
            "node_id": node_id,
            "node_role": node_role,
            "ttl_minutes": self.config.ttl_minutes,
        }

        try:
            response = requests.post(url, json=payload, timeout=10, verify=False)
            return AuthNodeResponse.model_validate_json(response.json())

        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.text
                    print(f"Error details: {error_detail}")
                except Exception as e:
                    print(f"Error details: {e}")
            raise
        
    async def _connect_camera_streamer(self, height: int, width: int):
        """
        Connect the robot's camera streamer to the operator's VR headset/display.
        Run this before calling send_stereo_frame or send_single_frame.
        """

        self.camera_streamer = LivekitCameraStreamer(height, width)
        
        await self.camera_streamer.start(
            livekit_data["room_name"],
            self.config.camera_participant,
            livekit_data["token"],
            livekit_data["livekit_url"],
        )
        
    
    # just make it a general 'connect'!
    async def connect_robot(self):
        """
        Connect the robot server to the operator.
        From now on the robot is ready for teleoperation.
        """
        
        # poll the webserver to check if the operator is ready
        # once ready,
            
        # Poll endpoint to see if operator is ready
        
        
        # Once operator is ready -> we set the operator_connected flag to True
        if connected:
            self.operator_connected = True
            
        await self.vr_controller.start(
            livekit_data["room_name"],
            self.config.controller_participant,
            livekit_data["token"],
            livekit_data["livekit_url"],
        )
    
    async def disconnect_robot(self):
        
        # send a disconnect post request to the webserver 
        
        

    
    async def disconnect_node(self):
            

    async def disconnect_controller(self):
        """
        Disconnect from the operator's controllers.
        Run this after you are finished with the operator's controllers.
        """
        if not self.vr_controller:
            return
        await self.vr_controller.stop()

    async def disconnect_camera_streamer(self):
        """
        Disconnect from the robot's camera streamer.
        Run this after you are finished with the camera streamer.
        """
        if not self.camera_streamer:
            return
        await self.camera_streamer.stop()
        
    

    async def send_stereo_frame(self, left_frame: np.ndarray, right_frame: np.ndarray):
        """Send the left and right frames of a stereo camera to the camera streamer.
           The frames should be horizontally concatenated.

        Args:
            frame (np.ndarray): The horizontally concatenated stereo frame, shape (height, 2*width, 3).

        Raises:
            ValueError: Camera streamer not connected
        """
        # connect the camera streamer (if it was not connected yet)

        if not self.operator_connected:
            return
        if not self.camera_streamer:
            raise ValueError("Camera streamer not connected")
        frame = np.concatenate([left_frame, right_frame], axis=1)
        await self.camera_streamer.send_stereo_frame(frame)
        await asyncio.sleep(0.001)

    async def send_single_frame(self, frame: np.ndarray):
        """Send the single frame from a mono camera to the camera streamer.

        Args:
            frame (np.ndarray): The single frame, shape (height, width, 3).

        Raises:
            ValueError: Camera streamer not connected
        """
        if not self.operator_connected:
            return
        if not self.camera_streamer:
            raise ValueError("Camera streamer not connected")
        await self.camera_streamer.send_single_frame(frame)
        
        
    

    async def get_controller_goal(self, arm: str) -> ArmGoal:
        """Get the VR Controller information.

        Args:
            arm (str): The arm to get the goal for.

        Returns:
            ArmGoal: Contains the following fields:
                - arm: left or right.
                - relative_transform: The relative transform of the VR Controller relative to the reference frame.
                - gripper_closed: False if trigger button is pressed, otherwise True.
                - reset_to_init: True if the the X, or A button is pressed, otherwise False.
                - reset_reference: True if the Grip button is activated, otherwise False.
                                   Sets the VR reference frame to the current frame.
        """
        if not self.pg_vr_controller:
            raise ValueError("VR controller not connected")
        await asyncio.sleep(0.001)
        return self.pg_vr_controller.get_controller_goal(arm)
    
    
    # additional subscriber and publisher node methods so you can do anything you want! (super extendible)
    async def send_data(self, data_name, data_target)
    
    
