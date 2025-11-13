from dataclasses import dataclass


@dataclass
class TactileTeleopConfig:
    backend_url: str = "https://10.5.1.246:8443/"
    controller_participant: str = "controllers-processing"
    camera_participant: str = "camera_streamer"
