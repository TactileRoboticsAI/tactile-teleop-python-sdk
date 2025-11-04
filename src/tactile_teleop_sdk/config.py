from dataclasses import dataclass
from typing import List, Optional
from dataclasses import field

from tactile_teleop_sdk.base_config import NodeConfig, TactileServerConfig, RawSubscriberConfig, RawPublisherConfig
from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig


from tactile_teleop_sdk.control_subscribers.base import BaseControlSubscriber, create_control_subscriber
from tactile_teleop_sdk.camera.camera_publisher.base import CameraSettings, create_camera_publisher, BaseCameraPublisher

@dataclass
class AuthConfig:
    email: str
    robot_id: str
    api_key: str

@dataclass
class ProtocolConfig:
    protocol: str = "livekit"
    ttl_minutes: int = 120

@dataclass
class ControlSubscriberConfig(NodeConfig):
    """Configuration for control subscriber"""
    node_id: str = "control_subscriber"
    controller_name: str = "ParallelGripperVRController"
    component_ids: List[str] = ["left", "right"]
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> BaseControlSubscriber:
        
        return create_control_subscriber(
            self.controller_name,
            self.component_ids,
            protocol_auth_config,
            node_id=self.node_id
        )

@dataclass
class CameraPublisherConfig(NodeConfig):
    """Configuration for camera streaming to operator"""
    node_id: str = "camera_publisher"
    frame_height: int = 480
    frame_width: int = 640
    max_framerate: int = 30
    max_bitrate: int = 3_000_000
    inter_pupillary_distance: float = 0.064 # set as a quick default now
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> BaseCameraPublisher:
        return create_camera_publisher(
            camera_type="livekit_vr",
            camera_settings=CameraSettings(
                height=self.frame_height,
                width=self.frame_width,
                max_framerate=self.max_framerate,
                max_bitrate=self.max_bitrate
            ),
            protocol_auth_config=protocol_auth_config
        )


__all__ = [
    "AuthConfig",
    "ProtocolConfig",
    "ControlSubscriberConfig",
    "CameraPublisherConfig",
]

@dataclass
class TeleopConfig:
    """"Complete teleop configuration - declare all the node configurations here"""
    auth: AuthConfig
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    server: TactileServerConfig = field(default_factory=TactileServerConfig)
    
    # Optional Specialized Node Configurations
    control_subscriber: Optional[ControlSubscriberConfig] = None
    camera_publisher: Optional[CameraPublisherConfig] = None
    
    # Optional Custom Node Configurations
    custom_subscribers: List[RawSubscriberConfig] = field(default_factory=list)
    custom_publishers: List[RawPublisherConfig] = field(default_factory=list)

