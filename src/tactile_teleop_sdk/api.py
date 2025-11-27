import asyncio
import logging
import os
import requests #type: ignore
from typing import Callable, Dict, Optional
from pathlib import Path

import numpy as np

from livekit import rtc
from pydantic import BaseModel
from typing import Literal, Any, List   
from dotenv import load_dotenv
from huggingface_hub import HfApi, login, auth_check
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from tactile_teleop_sdk.events import EventManager, EventType
from tactile_teleop_sdk.config import TactileConfig
from tactile_teleop_sdk.factory_configs import (
    ControlSubscriberConfig,
    CameraPublisherConfig,
    NodeConfig,
    OperatorSubscriberConfig,
)
from tactile_teleop_sdk.subscriber_node.base import BaseSubscriberNode
from tactile_teleop_sdk.publisher_node.base import BasePublisherNode
from tactile_teleop_sdk.protocol_auth import create_protocol_auth_config
from tactile_teleop_sdk.control_subscribers.base import BaseControlSubscriber
from tactile_teleop_sdk.camera.camera_publisher.base import BaseCameraPublisher
from tactile_teleop_sdk.control_subscribers.base import BaseControlGoal
from tactile_teleop_sdk.operator_subscribers.base import BaseOperatorSubscriber

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

    def __init__(self, config: TactileConfig):
        """
        Initialize the TactileAPI
        
        Args:
            config: Tactile configuration
        """
        # Auth and Protocol Configurations
        self.config = config
        self.__operator_connected = False

        # Event Manager
        self.__rooms: Dict[str, rtc.Room] = {}
        self.__event_manager = EventManager()

        # Node caches
        self._subscribers: dict[str, BaseSubscriberNode] = {}
        self._publishers: dict[str, BasePublisherNode] = {}

    async def _auth_node(self, node_id: str, node_role: Literal["subscriber", "publisher"]) -> AuthNodeResponse:
        """
        Authenticate Robot Node and get Protocol Authentication Token.
        """
        url = f"{self.config.server.backend_url}{self.config.server.auth_endpoint}"

        payload = {
            "robot_id": self.config.auth.robot_id,
            "api_key": self.config.auth.api_key,
            "protocol": self.config.protocol.protocol,
            "node_id": node_id,
            "node_role": node_role,
            "ttl_minutes": self.config.protocol.ttl_minutes,
        }

        try:
            response = requests.post(url, json=payload, timeout=10, verify=False)
            response.raise_for_status()
            return AuthNodeResponse.model_validate(response.json())

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

    async def _check_operator_status(self) -> bool:
        """Check if operator is currently connected"""
        url = f"{self.config.server.backend_url}/api/robot/check-operator-ready"
        payload = {
            "robot_id": self.config.auth.robot_id,
            "api_key": self.config.auth.api_key,
        }

        response = await asyncio.to_thread(requests.post, url, json=payload, timeout=10, verify=False)
        response.raise_for_status()

        status_data = OperatorConnectionStatusResponse.model_validate(response.json())
        self.__operator_connected = status_data.is_connected

        return status_data.is_connected

    async def wait_for_operator(self, poll_interval: float = 0.1, timeout: float = 300.0):
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
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Operator did not connect within {timeout} seconds")

            try:
                if await self._check_operator_status():
                    logging.info("✅ Operator connected, proceeding with protocol connection")
                    break

                logging.info(f"⏳ Waiting for operator to connect... ({elapsed:.1f}s elapsed)")

            except requests.RequestException as e:
                logging.error(f"❌ Failed to poll operator status: {e}")
                raise

            await asyncio.sleep(poll_interval)

    async def disconnect_robot(self):
        """Disconnect all nodes"""
        for node in self._subscribers.values():
            await node.disconnect()
        self._subscribers.clear()

        for node in self._publishers.values():
            await node.disconnect()
        self._publishers.clear()

        self.__operator_connected = False
        logging.info("✅ Monitoring stopped, all nodes disconnected")

    async def connect_controller(
        self,
        type: Literal["parallel_gripper_vr_controller"] = "parallel_gripper_vr_controller",
        robot_components: List[str] = ["left", "right"]) -> BaseControlSubscriber:

        if type == "parallel_gripper_vr_controller":
            config = ControlSubscriberConfig(
                node_id="vr_controller",
                controller_name="ParallelGripperVRController",
                component_ids=robot_components,
                subscribe_sources=["vr_controller"]
            )
        else:
            raise ValueError(f"Unknown controller type: {type}")

        return await self._ensure_node_connected(config, "subscriber")

    async def connect_operator(self) -> BaseOperatorSubscriber:
        config = OperatorSubscriberConfig(node_id="operator_subscriber", subscribe_sources=["operator"])
        return await self._ensure_node_connected(config, "subscriber")

    async def disconnect_controller(self, controller_id: str = "vr_controller"):
        """
        Disconnect a specific controller.
        
        Args:
            controller_id: Controller node identifier to disconnect
        """
        if controller_id in self._subscribers:
            await self._subscribers[controller_id].disconnect()
            del self._subscribers[controller_id]
            logging.info(f"✅ Controller '{controller_id}' disconnected")
        else:
            logging.warning(f"Controller '{controller_id}' not found")

    async def get_controller_goal(self, component_id: str, controller_id: str = "vr_controller") -> BaseControlGoal:
        """
        Get the control goal for a specific robot component.
        
        Args:
            component_id: Component identifier (e.g., "left", "right")
            controller_id: Controller node identifier (default: "vr_controller")
            
        Returns:
            Control goal for the specified component
        """
        if controller_id not in self._subscribers:
            raise ValueError(
                f"Controller '{controller_id}' not connected. "
                f"Call connect_vr_controller(controller_id='{controller_id}') first."
            )

        subscriber: BaseControlSubscriber = self._subscribers[controller_id]  # type: ignore
        return subscriber.get_control_goal(component_id)

    async def connect_camera(
        self,
        camera_name: str = "camera_0",
        height: int = 480,
        width: int = 640,
        max_framerate: int = 30,
        max_bitrate: int = 3_000_000
    ) -> BaseCameraPublisher:
        """
        Connect a camera streamer to send video to operator.
        
        Args:
            camera_id: Unique identifier for this camera (for multiple cameras)
            height: Frame height in pixels
            width: Frame width in pixels
            max_framerate: Maximum framerate in Hz
            max_bitrate: Maximum bitrate in bits/s
            
        Returns:
            Connected camera publisher instance
        """
        config = CameraPublisherConfig(
            node_id=f"camera_publisher_{camera_name}",
            frame_height=height,
            frame_width=width,
            max_framerate=max_framerate,
            max_bitrate=max_bitrate
        )

        return await self._ensure_node_connected(config, "publisher")

    async def disconnect_camera(self, camera_name: str = "camera_0"):
        """
        Disconnect a specific camera streamer.
        
        Args:
            camera_name: Camera name used when connecting (e.g., "camera_0")
        """
        camera_id = f"camera_publisher_{camera_name}"
        if camera_id in self._publishers:
            await self._publishers[camera_id].disconnect()
            del self._publishers[camera_id]
            logging.info(f"✅ Camera '{camera_id}' disconnected")
        else:
            logging.warning(f"Camera '{camera_id}' not found")

    async def send_stereo_frame(
        self, 
        left_frame: np.ndarray, 
        right_frame: np.ndarray, 
        camera_name: str = "camera_0"
    ):
        """
        Send stereo frames to operator.

        Args:
            left_frame: Left camera frame, shape (height, width, 3)
            right_frame: Right camera frame, shape (height, width, 3)
            camera_name: Camera name used when connecting (default: "camera_0")

        Raises:
            ValueError: Camera publisher not connected
        """
        if not self.__operator_connected:
            return

        camera_id = f"camera_publisher_{camera_name}"
        if camera_id not in self._publishers:
            raise ValueError(
                f"Camera '{camera_id}' not connected. "
                f"Call connect_camera_streamer(camera_id='{camera_id}') first."
            )

        camera_publisher: BaseCameraPublisher = self._publishers[camera_id]  # type: ignore
        frame = np.concatenate([left_frame, right_frame], axis=1)
        await camera_publisher.send_stereo_frame(frame)

    async def send_single_frame(self, frame: np.ndarray, camera_name: str = "camera_0"):
        """
        Send single frame to operator.

        Args:
            frame: Single camera frame, shape (height, width, 3)
            camera_name: Camera name used when connecting (default: "camera_0")

        Raises:
            ValueError: Camera publisher not connected
        """
        if not self.__operator_connected:
            return

        camera_id = f"camera_publisher_{camera_name}"
        if camera_id not in self._publishers:
            raise ValueError(
                f"Camera '{camera_id}' not connected. "
                f"Call connect_camera_streamer(camera_id='{camera_id}') first."
            )

        camera_publisher: BaseCameraPublisher = self._publishers[camera_id]  # type: ignore
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

    def on(self, event: str, callback: Callable) -> None:
        """Register custom event handlers

        Args:
            event: Event name (e.g. EventType.OPERATOR_CONNECTED)
            callback: Function to call when the event is emitted.

        """
        self.__event_manager.on(event, callback)

    def off(self, event: str, callback: Optional[Callable]) -> None:
        """Deregister custom event handlers

        Args:
            event: Event name (e.g. EventType.OPERATOR_UPLOAD)
            callback:
        """
        self.__event_manager.off(event, callback)

    def _bridge_node_room_events(self, node: Any, node_id: str, node_role: str, room_name: str) -> None:
        """
        Bridge LiveKit room events from a specific node to the central EventManager.

        Args:
            node: The node instance (subscriber or publisher)
            node_id: Unique node identifier
            node_role: "subscriber" or "publisher"
            room_name: LiveKit room name
        """
        # Extract room from node (works for both subscriber and publisher)
        room = None
        if hasattr(node, "room"):
            room = node.room
        elif hasattr(node, "_subscriber") and hasattr(node._subscriber, "room"):
            room = node._subscriber.room
        elif hasattr(node, "_publisher") and hasattr(node._publisher, "room"):
            room = node._publisher.room

        if not room or node_id in self._bridged_rooms:
            return

        # Store room reference
        self._rooms[node_id] = room
        self._bridged_rooms.add(node_id)

        # Create metadata for all events from this room
        def create_event_data(base_data: dict = None) -> dict:
            """Helper to add room context to event data"""
            data = {
                "node_id": node_id,
                "node_role": node_role,
                "room_name": room_name,
            }
            if base_data:
                data.update(base_data)
            return data

        # Bridge: participant_connected
        @room.on("participant_connected")
        def on_participant_connected(participant):
            asyncio.create_task(
                self.event_manager.emit(
                    EventType.PARTICIPANT_CONNECTED,
                    create_event_data(
                        {
                            "identity": participant.identity,
                            "sid": participant.sid,
                        }
                    ),
                )
            )
            logging.debug(f"🟢 [{node_id}] Participant connected: {participant.identity}")

        # Bridge: participant_disconnected
        @room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            asyncio.create_task(
                self.event_manager.emit(
                    EventType.PARTICIPANT_DISCONNECTED,
                    create_event_data(
                        {
                            "identity": participant.identity,
                            "sid": participant.sid,
                        }
                    ),
                )
            )
            logging.debug(f"🔴 [{node_id}] Participant disconnected: {participant.identity}")

        # Bridge: track_published
        @room.on("track_published")
        def on_track_published(publication, participant):
            asyncio.create_task(
                self.event_manager.emit(
                    "track_published",
                    create_event_data(
                        {
                            "track_kind": str(publication.kind),
                            "track_sid": publication.sid,
                            "participant_identity": participant.identity,
                            "participant_sid": participant.sid,
                        }
                    ),
                )
            )
            logging.debug(f"📹 [{node_id}] Track published: {publication.kind} by {participant.identity}")

        # Bridge: track_subscribed (for subscribers)
        if node_role == "subscriber":

            @room.on("track_subscribed")
            def on_track_subscribed(track, publication, participant):
                asyncio.create_task(
                    self.event_manager.emit(
                        "track_subscribed",
                        create_event_data(
                            {
                                "track_kind": str(track.kind),
                                "track_sid": track.sid,
                                "participant_identity": participant.identity,
                                "participant_sid": participant.sid,
                            }
                        ),
                    )
                )
                logging.debug(f"📺 [{node_id}] Track subscribed: {track.kind} from {participant.identity}")

        # Bridge: data_received (for subscribers)
        if node_role == "subscriber":

            @room.on("data_received")
            def on_data_received(packet: rtc.DataPacket):
                try:
                    # Try to decode as JSON
                    import json

                    data = json.loads(packet.data.decode("utf-8"))

                    # Emit generic data_received event
                    asyncio.create_task(
                        self.__event_manager.emit(
                            EventType.DATA_RECEIVED,
                            create_event_data(
                                {
                                    "data": data,
                                    "participant": packet.participant.identity if packet.participant else None,
                                }
                            ),
                        )
                    )

                    # Emit specific action events if present
                    if isinstance(data, dict) and "action" in data:
                        action = data["action"]
                        if action == "upload":
                            asyncio.create_task(
                                self.__event_manager.emit(EventType.OPERATOR_UPLOAD, create_event_data(data))
                            )
                        elif action == "record":
                            asyncio.create_task(
                                self.__event_manager.emit(EventType.OPERATOR_RECORD, create_event_data(data))
                            )

                        # Also emit action-specific event
                        asyncio.create_task(self.__event_manager.emit(f"action:{action}", create_event_data(data)))

                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Emit raw data if not JSON
                    asyncio.create_task(
                        self.__event_manager.emit(
                            EventType.DATA_RECEIVED,
                            create_event_data(
                                {
                                    "data": packet.data,
                                    "raw": True,
                                    "participant": packet.participant.identity if packet.participant else None,
                                }
                            ),
                        )
                    )

        # Bridge: connection_quality_changed
        @room.on("connection_quality_changed")
        def on_quality_changed(quality, participant):
            asyncio.create_task(
                self.__event_manager.emit(
                    "connection_quality_changed",
                    create_event_data(
                        {
                            "quality": str(quality),
                            "participant_identity": participant.identity,
                            "participant_sid": participant.sid,
                        }
                    ),
                )
            )

        # Bridge: connection_state_changed
        @room.on("connection_state_changed")
        def on_connection_state_changed(state):
            asyncio.create_task(
                self.__event_manager.emit(
                    "connection_state_changed",
                    create_event_data(
                        {
                            "state": str(state),
                        }
                    ),
                )
            )

        logging.info(f"🌉 Bridged LiveKit events for node '{node_id}' (room: {room_name})")

    def _check_hf_authenticate(self) -> bool:
        """Check if user is authenticated with Hugging Face Hub
        Returns:
            True if authenticated
            False if not authenticated
        """
        try:
            HfApi()
            return True
        except Exception as e:
            return False

    async def authenticate_hf(self) -> bool:
        """Autenticates with Hugging Face Hub using the environment variable 'HF_TOKEN'
        Returns:
            True if the authentication was successful
            False otherwise
        """
        token = os.getenv("HF_TOKEN")
        if token:
            login(token=token)
        else:
            login()
        if self._check_hf_authenticate():
            user = HfApi().whoami()
            logging.info(f"Authenticated with Hugging Face Hub as {user['name']}")
            return True
        else:
            logging.error(f"Failed to authenticated with HuggingFace Hub: {str(e)}")
            return False
