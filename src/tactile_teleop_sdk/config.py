from dataclasses import dataclass
from typing import Union, List, Optional


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
class TactileServerConfig:
    backend_url: str = "https://localhost:8443/" #"https://teleop.tactilerobotics.ai"
    auth_endpoint: str = "/api/robot/auth-node"


@dataclass
class ControlSubscriberConfig:
    """Configuration for control subscriber"""
    subscriber_name: str
    component_ids: List[str]
    node_id: Optional[str] = None

@dataclass
class MonoCameraConfig:
    frame_height: int
    frame_width: int
    
@dataclass
class StereoCameraConfig:
    frame_height: int
    frame_width: int
    inter_pupillary_distance: float
    
CameraConfig = Union[MonoCameraConfig, StereoCameraConfig]
@dataclass
class CameraPublisherConfig:
    """Configuration for camera publisher"""
    camera_config: CameraConfig
    node_id: str = "camera_publisher"


class LivekitConfig:
    vr_controller_participant: str = "controllers-processing"
    camera_participant: str = "camera_streamer"
    

