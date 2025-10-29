"""
Publisher node module for protocol-agnostic data publishing.

Supports multiple protocols via registry pattern:
- LiveKit (video/audio streaming)
- Future protocols can be added via @register_protocol decorator
"""

from tactile_teleop_sdk.publisher_node.base import (
    BasePublisherNode,
    BaseConnectionConfig,
    create_publisher,
    register_protocol,
)

# Import protocol implementations to trigger registration
from tactile_teleop_sdk.publisher_node.livekit import (
    LivekitPublisherNode,
    LivekitPublisherConnectionConfig,
)

__all__ = [
    "BasePublisherNode",
    "BaseConnectionConfig",
    "create_publisher",
    "register_protocol",
    "LivekitPublisherNode",
    "LivekitPublisherConnectionConfig",
]
