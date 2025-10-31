"""
Base classes and data structures for input providers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Any

from tactile_teleop_sdk.config import TeleopConfig

logger = logging.getLogger(__name__)


class BaseControlProvider(ABC):
    """Abstract base class for control providers."""

    def __init__(self, config: TeleopConfig, component_ids: List[str]):
        self.config = config
        self.queues: dict[str, asyncio.Queue] = {}
        self._create_queues(component_ids)
        
    @abstractmethod
    def _process_operator_data_queue(self, operator_data_queue: list, component_id: str) -> Any:
        """Process a list of control goals and return a single control goal."""
        pass 
        
    def _create_queues(self, component_ids: List[str]):
        for component_id in component_ids:
            self.queues[component_id] = asyncio.Queue()
        return self.queues
    
    def _get_queue(self, component_id: str) -> asyncio.Queue:
        return self.queues[component_id]

    async def send_control_goal(self, goal):
        """Send a control goal and add it to the queue"""
        try:
            self.queues[goal.component_id].put_nowait(goal)
        except asyncio.QueueFull:
            logger.warning(f"Queue full for component {goal.component_id}")
        except KeyError:
            logger.error(f"No queue found for component {goal.component_id}")
        except Exception as e:
            logger.error(f"Error sending control goal: {e}")

    def get_control_goal(self, component_id: str) -> Any:
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
        control_goal = self._process_operator_data_queue(operator_data_queue, component_id)
        return control_goal
