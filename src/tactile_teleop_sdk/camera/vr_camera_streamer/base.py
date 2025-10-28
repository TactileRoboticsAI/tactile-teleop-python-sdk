from abc import ABC, abstractmethod
from typing import Dict, Type
import numpy as np
from pydantic import BaseModel

class CameraSettings(BaseModel):
    height: int
    width: int
    max_framerate: int = 30
    max_bitrate: int = 3_000_000

class ProtocolConnectionConfig(BaseModel):
    room_name: str
    token: str
    protocol: str
    protocol_server_url: str

class VRCameraStreamer:
    def __init__(self, camera_settings: CameraSettings, connection_config: ProtocolConnectionConfig):
        self.height = camera_settings.height
        self.width = camera_settings.width
        self.max_framerate = camera_settings.max_framerate
        self.max_bitrate = camera_settings.max_bitrate
        
        # Camera Streamer Node Id and role
        self.node_id = "camera_streamer"
        self.node_role = "publisher"
        
        # Protocol connection config
        self.room_name = connection_config.room_name
        self.token = connection_config.token
        self.protocol_server_url = connection_config.protocol_server_url
        
        
    @abstractmethod
    async def connect(self):
        # overall connect logic
        
        # make abstract methods of the protocol to import here (use the code depending on the protocol value)
        pass
        
    @abstractmethod
    async def disconnect(self):
        pass
        
    @abstractmethod
    async def send_single_frame(self, frame: np.ndarray):
        pass
        
    @abstractmethod
    async def send_stereo_frame(self, frame: np.ndarray):
        pass
    
    
# Protocol Registry
_PROTOCOL_REGISTRY: Dict[str, Type[VRCameraStreamer]] = {}

def register_protocol(protocol_name: str):
    """Decorator to register protocol implementations"""
    def decorator(cls: Type[VRCameraStreamer]):
        _PROTOCOL_REGISTRY[protocol_name] = cls
        return cls
    return decorator

def get_protocol(camera_settings: CameraSettings, connection_config: ProtocolConnectionConfig) -> VRCameraStreamer:
    """Factory function to get protocol instance by name."""
    protocol_cls = _PROTOCOL_REGISTRY.get(connection_config.protocol)
    if not protocol_cls:
        raise ValueError(f"Unknown protocol: {connection_config.protocol}")
    return protocol_cls(camera_settings, connection_config)

# Facade Functions
async def connect(camera_settings: CameraSettings, connection_config: ProtocolConnectionConfig) -> None:
    """Connect to the protocol."""
    protocol_instance = get_protocol(camera_settings, connection_config)
    await protocol_instance.connect()

async def disconnect(camera_settings: CameraSettings, connection_config: ProtocolConnectionConfig) -> None:
    """Disconnect from the protocol."""
    protocol_instance = get_protocol(camera_settings, connection_config)
    await protocol_instance.disconnect()