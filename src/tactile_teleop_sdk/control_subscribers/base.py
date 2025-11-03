"""
Base classes and data structures for input providers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict, Type

from pydantic import BaseModel

from tactile_teleop_sdk.subscriber_node.base import BaseProtocolAuthConfig, BaseSubscriberNode, create_subscriber

logger = logging.getLogger(__name__)

class BaseOperatorEvent(BaseModel):
    component_id: str

class BaseControlGoal(BaseModel):  
    component_id: str

class BaseControlSubscriber(ABC):
    """Abstract base class for control providers using Bridge pattern.
    
    Combines control logic (abstraction) with transport layer (implementation)
    while keeping them decoupled. Automatically handles subscriber node creation
    and wiring.
    """

    def __init__(
        self, 
        component_ids: List[str],
        protocol_auth_config: BaseProtocolAuthConfig,
        node_id: Optional[str] = None
    ):
        """Initialize control provider with transport configuration.
        
        Args:
            config: High-level teleop configuration
            component_ids: List of robot components (e.g. ["left", "right"])
            connection_config: Protocol-specific connection config (required)
            node_id: Optional identifier for this node. Defaults to class name.
        """
        self.queues: dict[str, asyncio.Queue] = {}
        self._create_queues(component_ids)
        self._protocol_auth_config = protocol_auth_config
        self._node_id = node_id or self.__class__.__name__
        self._subscriber: Optional[BaseSubscriberNode] = None
        self._connected = False
        
    @abstractmethod
    def _process_operator_data_queue(self, operator_data_queue: list, component_id: str) -> Any:
        """Process a list of control goals and return a single control goal."""
        pass
    
    @abstractmethod
    async def _handle_incoming_data(self, data: dict) -> None:
        """Handle incoming data from transport layer.
        
        Template method for protocol-specific data parsing and processing.
        Should parse the data and call add_operator_data_to_queue() to queue goals.
        
        Args:
            data: Raw data received from subscriber node
        """
        pass
    
    async def connect(self) -> None:
        """Connect to transport layer and start receiving data."""
        if self._connected:
            logger.warning(f"({self._node_id}) Already connected to transport layer")
            return
        
        self._subscriber = create_subscriber(
            node_id=self._node_id,
            protocol_auth_config=self._protocol_auth_config
        )
        
        self._subscriber.register_data_callback(self._handle_incoming_data)
        
        await self._subscriber.connect()
        self._connected = True
        logger.info(f"({self._node_id}) ✅ Connected to transport layer and ready")
    
    async def disconnect(self) -> None:
        """Disconnect from transport layer."""
        if not self._connected or self._subscriber is None:
            return
        
        await self._subscriber.disconnect()
        self._subscriber = None
        self._connected = False
        logger.info(f"({self._node_id}) 🏁 Disconnected from transport layer")
        
    def _create_queues(self, component_ids: List[str]):
        for component_id in component_ids:
            self.queues[component_id] = asyncio.Queue()
        return self.queues
    
    def _get_queue(self, component_id: str) -> asyncio.Queue:
        return self.queues[component_id]

    async def add_operator_data_to_queue(self, operator_data: BaseOperatorEvent):
        """Send a control goal and add it to the queue"""
        try:
            self.queues[operator_data.component_id].put_nowait(operator_data)
        except asyncio.QueueFull:
            logger.warning(f"Queue full for component {operator_data.component_id}")
        except KeyError:
            logger.error(f"No queue found for component {operator_data.component_id}")
        except Exception as e:
            logger.error(f"Error sending operator data: {e}")

    def get_control_goal(self, component_id: str) -> BaseControlGoal:
        """Get a control goal from the queue."""
        
        queue = self._get_queue(component_id)
        
        # Drain queue
        operator_data_queue = []
        try:
            while True:
                operator_data_queue.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        
        # Calculate control goal
        control_goal: BaseControlGoal = self._process_operator_data_queue(operator_data_queue, component_id)
        return control_goal


# Control Subscriber Registry
_CONTROL_SUBSCRIBER_REGISTRY: Dict[str, Type[BaseControlSubscriber]] = {}


def register_control_subscriber(subscriber_name: str):
    """Decorator to register control subscriber implementations"""
    def decorator(cls: Type[BaseControlSubscriber]):
        _CONTROL_SUBSCRIBER_REGISTRY[subscriber_name] = cls
        return cls
    return decorator


def create_control_subscriber(
    subscriber_name: str,
    component_ids: List[str],
    connection_config: BaseProtocolAuthConfig,
    node_id: Optional[str] = None
) -> BaseControlSubscriber:
    """Factory function to create control subscriber instance by name"""
    subscriber_cls = _CONTROL_SUBSCRIBER_REGISTRY.get(subscriber_name)
    if not subscriber_cls:
        raise ValueError(
            f"Unknown control subscriber: {subscriber_name}. "
            f"Available: {list(_CONTROL_SUBSCRIBER_REGISTRY.keys())}"
        )
    return subscriber_cls(component_ids, connection_config, node_id)
