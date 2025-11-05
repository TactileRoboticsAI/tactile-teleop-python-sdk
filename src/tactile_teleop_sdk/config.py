import os
from dataclasses import dataclass
from typing import List
from dataclasses import field
from pydantic import BaseModel
from tactile_teleop_sdk.base_config import TactileServerConfig
from tactile_teleop_sdk.factory_configs import RawSubscriberConfig, RawPublisherConfig

class AuthConfig(BaseModel):
    robot_id: str
    api_key: str

@dataclass
class ProtocolConfig:
    protocol: str = "livekit"
    ttl_minutes: int = 120

@dataclass
class TactileConfig:
    """"Complete teleop configuration - declare all the node configurations here"""
    auth: AuthConfig
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    server: TactileServerConfig = field(default_factory=TactileServerConfig)
    
    # Optional Custom Node Configurations (for advanced users)
    custom_subscribers: List[RawSubscriberConfig] = field(default_factory=list)
    custom_publishers: List[RawPublisherConfig] = field(default_factory=list)
    
    @classmethod
    def from_env(
        cls,
        protocol: str = "livekit",
        ttl_minutes: int = 120
    ) -> "TactileConfig":
        """
        Create TactileConfig from environment variables.
        
        Args:
            protocol: Communication protocol to use (default: "livekit")
            ttl_minutes: Token time-to-live in minutes (default: 120)
        
        Environment variables required:
            TACTILE_ROBOT_ID: Robot identifier
            TACTILE_API_KEY: API authentication key
        """
        robot_id = os.getenv("TACTILE_ROBOT_ID")
        api_key = os.getenv("TACTILE_API_KEY")
        if not robot_id or not api_key:
            raise ValueError("TACTILE_ROBOT_ID and TACTILE_API_KEY must be set")
        
        return cls(
            auth=AuthConfig(
                robot_id=robot_id,
                api_key=api_key
            ),
            protocol=ProtocolConfig(
                protocol=protocol,
                ttl_minutes=ttl_minutes
            )
        )

__all__ = [
    "AuthConfig",
    "ProtocolConfig",
]
