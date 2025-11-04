"""
Base configuration infrasturcture for node management.
Advanced users can extend these for custom node types.
"""

from dataclasses import dataclass
from typing import Any
from abc import ABC, abstractmethod

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

