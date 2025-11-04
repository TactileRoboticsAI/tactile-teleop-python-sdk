import asyncio
import logging

import numpy as np
import requests
from pydantic import BaseModel
from typing import Literal, Optional, Callable, Any
from dotenv import load_dotenv

from tactile_teleop_sdk.camera.camera_publisher.base import BaseCameraPublisher, CameraSettings
from tactile_teleop_sdk.camera.camera_publisher.livekit import LivekitVRCameraStreamer
from tactile_teleop_sdk.config import AuthConfig, ProtocolConfig, TactileServerConfig, ControlSubscriberConfig, CameraPublisherConfig, MonoCameraConfig, StereoCameraConfig
from tactile_teleop_sdk.control_subscribers.base import BaseControlSubscriber, create_control_subscriber
from tactile_teleop_sdk.subscriber_node.base import BaseSubscriberNode, create_subscriber
from tactile_teleop_sdk.publisher_node.base import BasePublisherNode, create_publisher
from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig, create_protocol_auth_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")

load_dotenv()

class AuthNodeResponse(BaseModel):
    room_name: str
    token: str
    protocol_server_url: str
    expires_at: str

class OperatorConnectionStatusResponse(BaseModel):
    is_connected: bool

class TeleopAPI:
    def __init__(
        self, 
        tactile_auth_config: AuthConfig, 
        protocol_config: Optional[ProtocolConfig] = None):
        """
        Initialize the TactileAPI
        
        Args:
            tactile_auth_config: Authentication configuration
            protocol_config: Protocol configuration (defaults to ProtocolConfig())
        """
        # Auth and Protocol Configurations
        self.tactile_auth_config = tactile_auth_config
        self.protocol_config = protocol_config or ProtocolConfig()
        self.tactile_server_config = TactileServerConfig()
        
        # Configuring Control Subscriber
        
        
        # Configuring Camera Publisher
        
        
        self.operator_connected = False
        
        # Node instances (lazily initialized)
        self._subscribers: dict[str, BaseSubscriberNode] = {}
        self._publishers: dict[str, BasePublisherNode] = {}
        
        
    async def _auth_node(self, node_id: str, node_role: Literal["subscriber", "publisher"]) -> AuthNodeResponse:
        """
        Authenticate Robot Node and get Protocol Authentication Token.
        """
        url = f"{self.tactile_server_config.backend_url}{self.tactile_server_config.auth_endpoint}"

        payload = {
            "email": self.tactile_auth_config.email,
            "robot_id": self.tactile_auth_config.robot_id,
            "api_key": self.tactile_auth_config.api_key,
            "protocol": self.protocol_config.protocol,
            "node_id": node_id,
            "node_role": node_role,
            "ttl_minutes": self.protocol_config.ttl_minutes,
        }

        try:
            response = requests.post(url, json=payload, timeout=10, verify=False)
            return AuthNodeResponse.model_validate_json(response.json())

        except requests.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.text
                    print(f"Error details: {error_detail}")
                except Exception as e:
                    print(f"Error details: {e}")
            raise
    
    def _create_protocol_auth_config(self, auth_response: AuthNodeResponse, **kwargs) -> BaseProtocolAuthConfig:
        """Create protocol-specific connection config from auth response"""
        return create_protocol_auth_config(
            protocol=self.protocol_config.protocol,
            room_name=auth_response.room_name,
            token=auth_response.token,
            server_url=auth_response.protocol_server_url,
            **kwargs
        )
        
    async def _ensure_node_connected(
        self,
        node_id: str,
        node_role: Literal["subscriber", "publisher"],
        factory: Callable[[BaseProtocolAuthConfig], Any]
    ) -> Any:
        """
        Core connection logic - factory handles all node type customization.
        
        Args:
            node_id: Unique identifier for the node
            node_role: "subscriber" or "publisher" 
            factory: Function that takes protocol_auth_config and returns a node instance
        
        Returns:
            The connected node instance
        """
        # Select cache based on role
        cache = self._subscribers if node_role == "subscriber" else self._publishers
        
        # Check if already connected
        if node_id in cache:
            return cache[node_id]
        
        # Authenticate and create protocol auth config
        auth_response = await self._auth_node(node_id, node_role)
        protocol_auth_config = self._create_protocol_auth_config(auth_response)
        
        # Create node via factory
        node = factory(protocol_auth_config)
        
        # Connect node
        await node.connect()
        
        # Cache and return
        cache[node_id] = node
        logging.info(f"✅ Node '{node_id}' ({node_role}) connected successfully")
        return node




    

        
    async def connect_robot(self, poll_interval: float = 0.1, timeout: float = 300.0):
        """
        Connect the robot server to the operator.
        Polls the webserver until operator is connected, then establishes protocol connection.
        
        Args:
            poll_interval: Seconds between polling attempts (default: 0.1)
            timeout: Maximum seconds to wait for operator connection (default: 300.0)
        
        Raises:
            TimeoutError: If operator doesn't connect within timeout period
            requests.RequestException: If polling request fails
        """
        url = f"{self.tactile_server_config.backend_url}/api/robot/{self.tactile_auth_config.robot_id}/operator-connected"
        headers = {"Authorization": f"Bearer {self.tactile_auth_config.api_key}"}
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Operator did not connect within {timeout} seconds")
            
            try:
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
                
                status_data = OperatorConnectionStatusResponse.model_validate(response.json())
                
                if status_data.is_connected:
                    logging.info("✅ Operator connected, proceeding with protocol connection")
                    self.operator_connected = True
                    break
                    
                logging.info(f"⏳ Waiting for operator to connect... ({elapsed:.1f}s elapsed)")
                
            except requests.RequestException as e:
                logging.error(f"❌ Failed to poll operator status: {e}")
                raise
            
            await asyncio.sleep(poll_interval)
    
        
    async def disconnect_robot(self):
        """Disconnect all connected nodes (subscribers and publishers)"""
        # Disconnect all subscribers
        for node in self._subscribers.values():
            await node.disconnect()
        self._subscribers.clear()
        
        # Disconnect all publishers
        for node in self._publishers.values():
            await node.disconnect()
        self._publishers.clear()
        
        self.operator_connected = False
        logging.info("✅ All nodes disconnected")
        

    

    async def get_controller_goal(self, component_id: str) -> Any:
        """Get the control goal for a specific component (e.g., arm).

        Args:
            component_id: The component identifier (e.g., "left", "right")

        Returns:
            Control goal from the configured control subscriber
            
        Raises:
            ValueError: If control subscriber is not configured
        """
        
        self._control_subscriber = await self._ensure_node_connected(
            node_id=self.control_subscriber_config.node_id,
            node_role="subscriber",
            factory=lambda cfg: create_control_subscriber(
                self.control_subscriber_config.controller_name,
                self.control_subscriber_config.component_ids,
                cfg,
                self.control_subscriber_config.node_id
            )
        )
        return self._control_subscriber.get_control_goal(component_id)
    
        
    async def _ensure_camera_publisher(self) -> BaseCameraPublisher:
        """Lazily initialize and connect camera publisher"""
        if self.camera_publisher_config is None:
            raise ValueError("Camera publisher not configured")
        
        camera_settings = CameraSettings(
            height=self.camera_publisher_config.camera_config.frame_height,
            width=self.camera_publisher_config.camera_config.frame_width
        )
        
        return await self._ensure_node_connected(
            node_id=self.camera_publisher_config.node_id,
            node_role="publisher",
            factory=camera_factory
        )
        

    async def send_stereo_frame(self, left_frame: np.ndarray, right_frame: np.ndarray):
        """Send the left and right frames of a stereo camera to the camera streamer.

        Args:
            left_frame: Left camera frame, shape (height, width, 3)
            right_frame: Right camera frame, shape (height, width, 3)

        Raises:
            ValueError: Camera publisher not configured
        """
        if not self.operator_connected:
            return
        
        camera_publisher = await self._ensure_node_connected(node_id=self.camera_publisher_config.node_id, 
                                                             node_role="publisher",
                                                             factory=lambda cfg: create_publisher(self.camera_publisher_config.node_id, cfg))
            
            
        frame = np.concatenate([left_frame, right_frame], axis=1)
        await camera_publisher.send_stereo_frame(frame)
        await asyncio.sleep(0.001)

    async def send_single_frame(self, frame: np.ndarray):
        """Send the single frame from a mono camera to the camera streamer.

        Args:
            frame: The single frame, shape (height, width, 3)

        Raises:
            ValueError: Camera publisher not configured
        """
        if not self.operator_connected:
            return
        
        camera_publisher = await self._ensure_camera_publisher()
        await camera_publisher.send_single_frame(frame)
        
        
    


    
    
    # Custom node methods for fully extensible communication
    
    async def get_data(self, node_id: str) -> Optional[dict]:
        """
        Subscribe to a custom data stream using a raw subscriber node.
        
        This method allows users to create custom data subscriptions beyond
        the standard control and camera streams.
        
        Args:
            node_id: Unique identifier for the subscriber node
        
        Returns:
            Latest data received by the subscriber (implementation-specific)
            
        Example:
            # Subscribe to custom sensor data
            sensor_data = await api.get_data("custom_sensor_subscriber")
        """
        await self._ensure_node_connected(node_id, "subscriber", lambda cfg: create_subscriber(node_id, cfg))
        # Note: Actual data retrieval depends on how the subscriber is configured
        # Users would typically register their own callback via subscriber.register_data_callback()
        # This is a low-level method that gives full control
        return None  # Placeholder - users configure callbacks themselves
    
    async def send_data(self, node_id: str, data: Any):
        """
        Publish custom data using a raw publisher node.
        
        This method allows users to send arbitrary data beyond the standard
        camera frames.
        
        Args:
            node_id: Unique identifier for the publisher node
            data: Data to send (will be passed to publisher's send_data method)
            
        Example:
            # Send custom telemetry data
            await api.send_data("telemetry_publisher", {"speed": 1.5, "battery": 85})
        """
        publisher = await self._ensure_custom_publisher(node_id)
        await publisher.send_data(data)
