from dataclasses import dataclass


@dataclass
class TactileTeleopConfig:
    backend_url: str = "https://teleop.tactilerobotics.ai"
    controller_participant: str = "controllers-processing"
    camera_participant: str = "camera_streamer"
