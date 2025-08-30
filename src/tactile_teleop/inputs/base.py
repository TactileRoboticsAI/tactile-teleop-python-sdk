"""
Base classes and data structures for input providers.
"""

import numpy as np

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Control goal types."""

    IDLE = "idle"  # No button on vr controller pressed
    GRIP_ACTIVE_INIT = "grip_active_init"  # Grip button pressed first time
    GRIP_ACTIVE = "grip_active"  # Grip button held
    GRIP_RELEASE = "grip_release"  # Grip button released
    TRIGGER_ACTIVE = "trigger_active"  # Trigger button pressed
    TRIGGER_RELEASE = "trigger_release"  # Trigger button released
    RESET_BUTTON_RELEASE = "reset_button_release"  # Reset button released


@dataclass
class ControlGoal:
    """Control goal."""

    event_type: EventType
    arm: str
    origin_transform: Optional[np.ndarray] = None
    target_transform: Optional[np.ndarray] = None
    gripper_closed: Optional[bool] = None


class BaseInputProvider(ABC):
    """Abstract base class for input providers."""

    @abstractmethod
    async def start(self, *args, **kwargs):
        """Start the input provider."""
        pass

    @abstractmethod
    async def stop(self, *args, **kwargs):
        """Stop the input provider."""
        pass