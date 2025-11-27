import asyncio
import logging
from enum import Enum
from typing import List, Dict, Callable, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard event types emitted by the SDK"""

    OPERATOR_CONNECTED = "operator_connected"
    OPERATOR_DISCONNECTED = "operator_disconnected"
    PARTICIPANT_CONNECTED = "participant_connected"
    PARTICIPANT_DISCONNECTED = "participant_disconnected"
    DATA_RECEIVED = "data_received"
    OPERATOR_UPLOAD = "operator_upload"
    OPERATOR_RECORD = "operator_record"


class EventManager:
    """Manages events, event listeners and dispatching across the SDK"""

    _listeners: Dict[str, Callable] = {}

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for a specific event type
        Args:
            event: Name of the event
            callback: Specific callback to add
        """
        event_name = event.value if isinstance(event, EventType) else event

        if event_name not in self._listeners:
            self._listeners[event_name] = []

        self._listeners[event_name].append(callback)
        logger.info(f"Reistered listener for event: {event_name}")

    def off(self, event: str, callback: Optional[Callable]) -> None:
        """Deregister callback(s) for a specific event type

        Args:
            event: Name of the event
            callback: Specific callback to remove, or None. If None, then all callbacks are removed.
        """
        event_name = event.value if isinstance(event, EventType) else event

        if event_name not in self._listeners:
            return

        if callback is None:
            del self._listeners[event_name]
            logger.info(f"Removed all listeners for event")

        elif callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    async def emit(self, event: str, data: any = None) -> None:
        """Emit an event to all registered event listeners

        Args:
            event: Name of the event
            data: Payload data of the event
        """
        event_name = event.value if isinstance(event, EventType) else event

        if event_name not in self._listeners:
            return

        logger.debug(f"Emitting event: {event_name} with data {data}")

        for callback in self._listeners[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in event listeners for {event_name}: {e}", exc_info=True)
