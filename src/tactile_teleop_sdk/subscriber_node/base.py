from abc import ABC, abstractmethod
from typing import Dict, Type, Callable, Awaitable, Optional
from pydantic import BaseModel


class BaseConnectionConfig(BaseModel):
    """Base configuration for protocol connections"""
    protocol: str
    room_name: str


class BaseSubscriberNode(ABC):
    """Abstract base for protocol-agnostic subscriber nodes"""
    
    def __init__(self, node_id: str, connection_config: BaseConnectionConfig):
        self.node_id = node_id
        self.connection_config = connection_config
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
    connection_config: BaseConnectionConfig
) -> BaseSubscriberNode:
    """Factory function to create subscriber instance by protocol"""
    protocol_cls = _PROTOCOL_REGISTRY.get(connection_config.protocol)
    if not protocol_cls:
        raise ValueError(
            f"Unknown protocol: {connection_config.protocol}. "
            f"Available: {list(_PROTOCOL_REGISTRY.keys())}"
        )
    return protocol_cls(node_id, connection_config)
