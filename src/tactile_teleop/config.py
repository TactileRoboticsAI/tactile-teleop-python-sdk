from dataclasses import dataclass, field
from enum import Enum

import cv2


class InputType(Enum):
    VR_CONTROLLER = "vr_controller"


@dataclass
class TactileTeleopConfig:
    input_type: InputType = InputType.VR_CONTROLLER
    livekit_room: str = "robot-vr-teleop-room"
    camera_streamer_participant: str = "camera-streamer"
    controllers_processing_participant: str = "controllers-processing"
    controllers_publishing_participant: str = "controllers-publishing"
    vr_viewer_participant: str = "vr-viewer"
    camera_config: dict = field(
        default_factory=lambda: {
            "dual_camera_opencv": {
                "type": "dual_camera_opencv",
                "edge_crop_pixels": 60,
                "calibration_file": "src/tactile_teleop/camera/calibration/stereo_calibration_vr_20250804_145002.pkl",
                "cam_index_left": 4,
                "cam_index_right": 6,
                "cap_backend": cv2.CAP_V4L2,
            }
        }
    )
