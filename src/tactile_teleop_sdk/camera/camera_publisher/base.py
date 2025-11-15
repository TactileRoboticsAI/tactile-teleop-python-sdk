import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Type
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
    max_framerate: int
    max_bitrate: int


class BaseCameraPublisher(ABC):
    """
    (stereo) camera streamer to VR headset/display.
    """
    
    def __init__(
        self,
        camera_settings: CameraSettings,
        protocol_auth_config: BaseProtocolAuthConfig,
        node_id: str
    ):
        self.camera_settings = camera_settings
        self.protocol_auth_config = protocol_auth_config
        self.node_id = node_id
        
        self.publisher: BasePublisherNode | None = None
    
    async def connect(self, **publisher_kwargs) -> None:
        """Initialize publisher and establish connection"""
        self.publisher = create_publisher(
            self.node_id,
            self.protocol_auth_config,
            **publisher_kwargs
        )
        print(f"Creating publisher with node_id: {self.node_id} and protocol_auth_config: {self.protocol_auth_config}")
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


_CAMERA_PUBLISHER_REGISTRY: Dict[str, Type[BaseCameraPublisher]] = {}


def register_camera_publisher(camera_type: str):
    """Decorator to register camera publisher implementations"""
    def decorator(cls: Type[BaseCameraPublisher]):
        _CAMERA_PUBLISHER_REGISTRY[camera_type] = cls
        return cls
    return decorator


def create_camera_publisher(
    camera_type: str,
    camera_settings: CameraSettings,
    protocol_auth_config: BaseProtocolAuthConfig,
    **kwargs
) -> BaseCameraPublisher:
    """Factory function to create camera publisher instance by type"""
    publisher_cls = _CAMERA_PUBLISHER_REGISTRY.get(camera_type)
    if not publisher_cls:
        raise ValueError(
            f"Unknown camera publisher: {camera_type}. "
            f"Available: {list(_CAMERA_PUBLISHER_REGISTRY.keys())}"
        )
    return publisher_cls(camera_settings, protocol_auth_config, **kwargs)
