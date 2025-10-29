from dataclasses import dataclass
from typing import Literal, Union


@dataclass
class TeleopConfig:
    api_key: str
    protocol: str = "webrtc"
    stream_camera: bool = True
    ttl_minutes: int = 120
    gripper_type: Literal["parallel", "hand"] = "parallel"

class MonoCameraConfig:
    frame_height: int
    frame_width: int
    
class StereoCameraConfig:
    frame_height: int
    frame_width: int
    inter_pupillary_distance: float
    
CameraConfig = Union[MonoCameraConfig, StereoCameraConfig]

class LivekitConfig:
    vr_controller_participant: str = "controllers-processing"
    camera_participant: str = "camera_streamer"
    
    
# These will be hidden from the user:
class EnvVariables:
    backend_url: str = "https://localhost:8443/" #"https://teleop.tactilerobotics.ai"
    auth_endpoint: str = "api/robot/auth-node"


# Idea
# -> what type of controller that we use needs to come from the webserver
# -> mappigng: key -> Controller type