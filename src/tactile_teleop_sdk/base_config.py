"""
Base configuration infrasturcture for node management.
Advanced users can extend these for custom node types.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any
from abc import ABC, abstractmethod

from tactile_teleop_sdk.config import AuthConfig, ProtocolConfig, ControlSubscriberConfig, CameraPublisherConfig
from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig
from tactile_teleop_sdk.subscriber_node.base import create_subscriber
from tactile_teleop_sdk.publisher_node.base import create_publisher

@dataclass
class TactileServerConfig:
    backend_url: str = "https://localhost:8443/" #"https://teleop.tactilerobotics.ai"
    auth_endpoint: str = "/api/robot/auth-node"


@dataclass
class NodeConfig(ABC):
    """Base class for all node configurations"""
    node_id: str
    
    @abstractmethod
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        """Factory Method to create the node instance"""
        pass

@dataclass
class RawSubscriberConfig(NodeConfig):
    """Configuration for raw subscriber nodes (custom data streams)"""
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        return create_subscriber(self.node_id, protocol_auth_config)
    
    
@dataclass
class RawPublisherConfig(NodeConfig):
    """Configuration for raw publisher nodes (custom data streams)"""
    
    def create_node(self, protocol_auth_config: BaseProtocolAuthConfig) -> Any:
        return create_publisher(self.node_id, protocol_auth_config)

@dataclass
class TeleopConfig:
    """"Complete teleop configuration - declare all the node configurations here"""
    auth: AuthConfig
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    server: TactileServerConfig = field(default_factory=TactileServerConfig)
    
    # Optional Specialized Node Configurations
    control_subscriber: Optional[ControlSubscriberConfig] = None
    camera_publisher: Optional[CameraPublisherConfig] = None
    
    # Optional Custom Node Configurations
    custom_subscribers: List[RawSubscriberConfig] = field(default_factory=list)
    custom_publishers: List[RawPublisherConfig] = field(default_factory=list)

