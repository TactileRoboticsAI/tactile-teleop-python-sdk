from dataclasses import dataclass, field
from enum import Enum


class InputType(Enum):
    VR_CONTROLLER = "vr_controller"


@dataclass
class CameraConfig:
    stereo_camera: bool = False
    width: int = 580
    height: int = 480


@dataclass
class TactileTeleopConfig:
    input_type: InputType = InputType.VR_CONTROLLER
    livekit_room: str = "robot-vr-teleop-room"
    camera_streamer_participant: str = "camera-streamer"
    controllers_processing_participant: str = "controllers-processing"
    controllers_publishing_participant: str = "controllers-publishing"
    vr_viewer_participant: str = "vr-viewer"
    camera_config: CameraConfig = field(default_factory=CameraConfig)
