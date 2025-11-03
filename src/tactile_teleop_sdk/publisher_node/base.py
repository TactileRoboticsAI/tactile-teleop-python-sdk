from abc import ABC, abstractmethod
from typing import Dict, Type, Any

from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig


class BasePublisherNode(ABC):
    """Abstract base for protocol-agnostic publisher nodes"""
    
    def __init__(self, node_id: str, protocol_auth_config: BaseProtocolAuthConfig):
        self.node_id = node_id
        self.protocol_auth_config = protocol_auth_config
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the protocol server"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the protocol server"""
        pass
    
    @abstractmethod
    async def send_data(self, data: Any) -> None:
        """Send arbitrary data through the publisher"""
        pass


# Protocol Registry
_PROTOCOL_REGISTRY: Dict[str, Type[BasePublisherNode]] = {}


def register_protocol(protocol_name: str):
    """Decorator to register protocol implementations"""
    def decorator(cls: Type[BasePublisherNode]):
        _PROTOCOL_REGISTRY[protocol_name] = cls
        return cls
    return decorator


def create_publisher(
    node_id: str, 
    protocol_auth_config: BaseProtocolAuthConfig
) -> BasePublisherNode:
    """Factory function to create publisher instance by protocol"""
    protocol_cls = _PROTOCOL_REGISTRY.get(protocol_auth_config.protocol)
    if not protocol_cls:
        raise ValueError(
            f"Unknown protocol: {protocol_auth_config.protocol}. "
            f"Available: {list(_PROTOCOL_REGISTRY.keys())}"
        )
    return protocol_cls(node_id, protocol_auth_config)
