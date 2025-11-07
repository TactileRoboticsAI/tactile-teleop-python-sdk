from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any, Literal
from dataclasses import field

from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig
from tactile_teleop_sdk.subscriber_node.base import create_subscriber
from tactile_teleop_sdk.publisher_node.base import create_publisher

from tactile_teleop_sdk.control_subscribers.base import BaseControlSubscriber, create_control_subscriber
from tactile_teleop_sdk.camera.camera_publisher.base import CameraSettings, create_camera_publisher, BaseCameraPublisher


@dataclass
class NodeConfig(ABC):
    """Base class for all node configurations"""
    node_id: str
    
    @abstractmethod
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        """Factory Method to create the node instance"""
        pass

@dataclass
class RawSubscriberConfig(NodeConfig):
    """Configuration for raw subscriber nodes (custom data streams)"""
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        return create_subscriber(self.node_id, protocol_auth_config)
    
@dataclass
class RawPublisherConfig(NodeConfig):
    """Configuration for raw publisher nodes (custom data streams)"""
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        return create_publisher(self.node_id, protocol_auth_config)

@dataclass
class ControlSubscriberConfig(NodeConfig):
    """Configuration for control subscriber"""
    node_id: str
    controller_name: Literal["ParallelGripperVRController"]
    component_ids: List[str]
    subscribe_sources: List[str] = field(default_factory=list)
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> BaseControlSubscriber:
        
        return create_control_subscriber(
            self.controller_name,
            self.component_ids,
            protocol_auth_config,
            node_id=self.node_id,
            subscribe_sources=self.subscribe_sources
        )
        
@dataclass
class CameraPublisherConfig(NodeConfig):
    """Configuration for camera streaming to operator"""
    node_id: str
    frame_height: int
    frame_width: int
    max_framerate: int
    max_bitrate: int 
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> BaseCameraPublisher:
        return create_camera_publisher(
            camera_settings=CameraSettings(
                height=self.frame_height,
                width=self.frame_width,
                max_framerate=self.max_framerate,
                max_bitrate=self.max_bitrate
            ),
            protocol_auth_config=protocol_auth_config,
            camera_type="livekit_vr",
            node_id=self.node_id
        )

