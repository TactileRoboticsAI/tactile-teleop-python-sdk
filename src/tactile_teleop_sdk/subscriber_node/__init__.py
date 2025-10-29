"""
Subscriber node module for protocol-agnostic data receiving.

Supports multiple protocols via registry pattern:
- LiveKit (video/audio streaming)
- Future protocols can be added via @register_protocol decorator
"""

from tactile_teleop_sdk.subscriber_node.base import (
    BaseSubscriberNode,
    BaseConnectionConfig,
    create_subscriber,
    register_protocol,
)

# Import protocol implementations to trigger registration
from tactile_teleop_sdk.subscriber_node.livekit import (
    LivekitSubscriberNode,
    LivekitSubscriberConnectionConfig,
)

__all__ = [
    "BaseSubscriberNode",
    "BaseConnectionConfig",
    "create_subscriber",
    "register_protocol",
    "LivekitSubscriberNode",
    "LivekitSubscriberConnectionConfig",
]
