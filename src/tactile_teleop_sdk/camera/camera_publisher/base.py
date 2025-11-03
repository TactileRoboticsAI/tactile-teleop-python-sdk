import numpy as np
from abc import ABC, abstractmethod
from pydantic import BaseModel

from tactile_teleop_sdk.publisher_node.base import (
    BasePublisherNode,
    BaseProtocolAuthConfig,
    create_publisher,
)


class CameraSettings(BaseModel):
    """Configuration for camera dimensions and encoding"""
    height: int
    width: int
    max_framerate: int = 30
    max_bitrate: int = 3_000_000


class BaseCameraPublisher(ABC):
    """
    (stereo) camera streamer to VR headset/display.
    """
    
    def __init__(
        self,
        camera_settings: CameraSettings,
        protocol_auth_config: BaseProtocolAuthConfig
    ):
        self.camera_settings = camera_settings
        self.protocol_auth_config = protocol_auth_config
        self.node_id = "vr_camera_streamer"
        self.publisher: BasePublisherNode | None = None
    
    async def connect(self) -> None:
        """Initialize publisher and establish connection"""
        self.publisher = create_publisher(self.node_id, self.protocol_auth_config)
        await self.publisher.connect()
    
    async def disconnect(self) -> None:
        """Disconnect from the publisher"""
        if self.publisher:
            await self.publisher.disconnect()
            self.publisher = None
    
    async def send_single_frame(self, frame: np.ndarray) -> None:
        """Send a single camera frame (duplicated for stereo)"""
        concatenated_frame = np.concatenate([frame, frame], axis=1)
        await self.send_stereo_frame(concatenated_frame)
    
    @abstractmethod
    async def send_stereo_frame(self, frame: np.ndarray) -> None:
        """Send a pre-concatenated stereo frame"""
        pass
