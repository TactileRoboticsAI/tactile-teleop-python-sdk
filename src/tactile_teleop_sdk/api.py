import asyncio
import logging
import requests #type: ignore

import numpy as np

from pydantic import BaseModel
from typing import Literal, Any
from dotenv import load_dotenv

from tactile_teleop_sdk.base_config import NodeConfig
from tactile_teleop_sdk.config import TactileConfig
from tactile_teleop_sdk.subscriber_node.base import BaseSubscriberNode
from tactile_teleop_sdk.publisher_node.base import BasePublisherNode
from tactile_teleop_sdk.protocol_auth import create_protocol_auth_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s")

load_dotenv()

class AuthNodeResponse(BaseModel):
    room_name: str
    token: str
    protocol_server_url: str
    expires_at: str

class OperatorConnectionStatusResponse(BaseModel):
    is_connected: bool

class TactileAPI:
    def __init__(
        self, config: TactileConfig):
        """
        Initialize the TactileAPI
        
        Args:
            config: Tactile configuration
        """
        # Auth and Protocol Configurations
        self.config = config
        self.operator_connected = False
        
        # Node caches
        self._subscribers: dict[str, BaseSubscriberNode] = {}
        self._publishers: dict[str, BasePublisherNode] = {}
        
        
    async def _auth_node(self, node_id: str, node_role: Literal["subscriber", "publisher"]) -> AuthNodeResponse:
        """
        Authenticate Robot Node and get Protocol Authentication Token.
        """
        url = f"{self.config.server.backend_url}{self.config.server.auth_endpoint}"

        payload = {
            "email": self.config.auth.email,
            "robot_id": self.config.auth.robot_id,
            "api_key": self.config.auth.api_key,
            "protocol": self.config.protocol.protocol,
            "node_id": node_id,
            "node_role": node_role,
            "ttl_minutes": self.config.protocol.ttl_minutes,
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
        
        
    async def _ensure_node_connected(
        self,
        node_config: NodeConfig,
        node_role: Literal["subscriber", "publisher"]
    ) -> Any:
        """
        Unified connection logic for all node types.
        
        Returns:
            The connected node instance
        """
        # Select cache based on role
        cache = self._subscribers if node_role == "subscriber" else self._publishers
        
        # Check if already connected
        if node_config.node_id in cache:
            return cache[node_config.node_id]
        
        # Authenticate
        auth_response = await self._auth_node(node_config.node_id, node_role)
        protocol_auth_config =  create_protocol_auth_config(
            protocol=self.config.protocol.protocol,
            room_name=auth_response.room_name,
            token=auth_response.token,
            server_url=auth_response.protocol_server_url,
        )
        
        # Create node via factory
        node = node_config.create_node(protocol_auth_config)
        
        # Connect node
        await node.connect()
        
        # Cache and return
        cache[node_config.node_id] = node
        logging.info(f"✅ Node '{node_config.node_id}' ({node_role}) connected successfully")
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
        url = f"{self.config.server.backend_url}/api/robot/{self.config.auth.robot_id}/operator-connected"
        headers = {"Authorization": f"Bearer {self.config.auth.api_key}"}
        
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
        """Get the control goal for a specific robot component (e.g. left arm) - auto-connects the control subscriber if not already connected
        """
        if not self.config.control_subscriber:
            raise ValueError("Control subscriber not configured")
        
        subscriber = await self._ensure_node_connected(
            node_config=self.config.control_subscriber,
            node_role="subscriber",
        )
        return subscriber.get_control_goal(component_id)
    

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
        
        if not self.config.camera_publisher:
            raise ValueError("Camera publisher not configured")
        
        camera_publisher = await self._ensure_node_connected(
            node_config=self.config.camera_publisher,
            node_role="publisher",
        )
        frame = np.concatenate([left_frame, right_frame], axis=1)
        await camera_publisher.send_stereo_frame(frame)


    async def send_single_frame(self, frame: np.ndarray):
        """Send the single frame from a mono camera to the camera streamer.

        Args:
            frame: The single frame, shape (height, width, 3)

        Raises:
            ValueError: Camera publisher not configured
        """
        if not self.operator_connected:
            return
        
        if not self.config.camera_publisher:    
            raise ValueError("Camera publisher not configured")
        
        camera_publisher = await self._ensure_node_connected(
            node_config=self.config.camera_publisher,
            node_role="publisher",
        )
        await camera_publisher.send_single_frame(frame)
    
    
    # Custom node methods for fully extensible communication
    async def get_subscriber(self, node_id: str) -> BaseSubscriberNode:
        """
        Get a raw subscriber node for custom data streams - auto-connects if needed.
        
        This method allows users to access custom subscriber nodes beyond
        the standard control subscriber.
        
        Args:
            node_id: Unique identifier for the subscriber node
        
        Returns:
            The connected subscriber node instance
            
        Raises:
            ValueError: If no subscriber config found for node_id
            
        Example:
            # Get custom sensor subscriber
            sensor_sub = await api.get_subscriber("custom_sensor")
            sensor_sub.register_data_callback(my_callback)
        """
        if not self.config.custom_subscribers:
            raise ValueError("No custom subscribers configured")
        
        config = next(
            (c for c in self.config.custom_subscribers if c.node_id == node_id),
            None
        )
        if not config:
            raise ValueError(
                f"No subscriber config found for '{node_id}'. "
                f"Available: {[c.node_id for c in self.config.custom_subscribers]}"
            )
        
        return await self._ensure_node_connected(config, "subscriber")
    
    async def get_publisher(self, node_id: str) -> BasePublisherNode:
        """
        Get a raw publisher node for custom data streams - auto-connects if needed.
        
        This method allows users to access custom publisher nodes beyond
        the standard camera publisher.
        
        Args:
            node_id: Unique identifier for the publisher node
        
        Returns:
            The connected publisher node instance
            
        Raises:
            ValueError: If no publisher config found for node_id
            
        Example:
            # Get custom telemetry publisher
            telemetry_pub = await api.get_publisher("telemetry")
            await telemetry_pub.send_data({"speed": 1.5, "battery": 85})
        """
        if not self.config.custom_publishers:
            raise ValueError("No custom publishers configured")
        
        config = next(
            (c for c in self.config.custom_publishers if c.node_id == node_id),
            None
        )
        if not config:
            raise ValueError(
                f"No publisher config found for '{node_id}'. "
                f"Available: {[c.node_id for c in self.config.custom_publishers]}"
            )
        
        return await self._ensure_node_connected(config, "publisher")
