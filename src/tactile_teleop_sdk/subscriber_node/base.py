from abc import ABC, abstractmethod
from typing import Dict, Type, Callable, Awaitable, Optional, List

from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig


class BaseSubscriberNode(ABC):
    """Abstract base for protocol-agnostic subscriber nodes"""
    
    def __init__(self, node_id: str, protocol_auth_config: BaseProtocolAuthConfig, subscribe_sources: List[str]):
        self.node_id = node_id
        self.protocol_auth_config = protocol_auth_config
        self.subscribe_sources = subscribe_sources
        self._data_callback: Optional[Callable[[Dict], Awaitable[None]]] = None
    
    def register_data_callback(self, callback: Callable[[Dict], Awaitable[None]]) -> None:
        """Register callback to process incoming data"""
        self._data_callback = callback
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the protocol server"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the protocol server"""
        pass
    

# Protocol Registry
_PROTOCOL_REGISTRY: Dict[str, Type[BaseSubscriberNode]] = {}


def register_protocol(protocol_name: str):
    """Decorator to register protocol implementations"""
    def decorator(cls: Type[BaseSubscriberNode]):
        _PROTOCOL_REGISTRY[protocol_name] = cls
        return cls
    return decorator


def create_subscriber(
    node_id: str, 
    protocol_auth_config: BaseProtocolAuthConfig,
    **kwargs
) -> BaseSubscriberNode:
    """Factory function to create subscriber instance by protocol"""
    protocol_cls = _PROTOCOL_REGISTRY.get(protocol_auth_config.protocol)
    if not protocol_cls:
        raise ValueError(
            f"Unknown protocol: {protocol_auth_config.protocol}. "
            f"Available: {list(_PROTOCOL_REGISTRY.keys())}"
        )
    return protocol_cls(node_id, protocol_auth_config, **kwargs)
