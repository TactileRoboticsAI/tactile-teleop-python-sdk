import logging
from typing import Any

from livekit import rtc
from pydantic import Field

from tactile_teleop_sdk.publisher_node.base import (
    BasePublisherNode,
    BaseConnectionConfig,
    register_protocol,
)

logger = logging.getLogger(__name__)


class LivekitPublisherConnectionConfig(BaseConnectionConfig):
    protocol: str = "livekit"
    livekit_url: str
    token: str
    track: rtc.LocalTrack = Field(exclude=True)
    track_publish_options: rtc.TrackPublishOptions = Field(exclude=True)


@register_protocol("livekit")
class LivekitPublisherNode(BasePublisherNode):
    """LiveKit implementation of publisher node"""
    
    def __init__(self, node_id: str, connection_config: LivekitPublisherConnectionConfig):
        super().__init__(node_id, connection_config)
        self.connection_config: LivekitPublisherConnectionConfig = connection_config
        self.room: rtc.Room | None = None
        
    async def _publish_track(self) -> None:
        """Publish the configured track to the room"""
        if not self.room:
            raise RuntimeError("Room not connected")
            
        try:
            await self.room.local_participant.publish_track(
                self.connection_config.track,
                self.connection_config.track_publish_options
            )
            logger.debug(f"({self.node_id}) Published track successfully")
        except Exception as e:
            logger.error(f"({self.node_id}) Failed to publish track: {e}", exc_info=True)
            raise

    async def connect(self) -> None:
        """Connect to LiveKit room and publish configured track"""
        self.room = rtc.Room()

        @self.room.on("participant_connected")
        def on_participant_connected(participant):
            logger.debug(f"🟢 Node connected: {participant.identity}")

        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            logger.debug(f"🔴 Node disconnected: {participant.identity}")

        @self.room.on("track_published")
        def on_track_published(publication, participant):
            logger.debug(f"📹 Track published by {participant.identity}: {publication.kind}")
        
        try:
            await self.room.connect(self.connection_config.livekit_url, self.connection_config.token)
            
            # Log connection state
            logger.debug(f"✅ Connected to LiveKit room {self.connection_config.room_name} as node {self.node_id}")
            logger.debug(f"🔍 Room connection state: {self.room.connection_state}")
            logger.debug(f"🔍 Local node (should = {self.node_id}): {self.room.local_participant.identity}")
            logger.debug(f"📊 Remote room nodes: {len(self.room.remote_participants)}")
            for participant in self.room.remote_participants.values():
                logger.debug(f"  - {participant.identity} ({participant.sid})")

            await self._publish_track()

        except KeyboardInterrupt:
            logger.debug(f"({self.node_id}) ⌨️  KeyboardInterrupt, shutting down")
            raise
        except Exception as e:
            logger.error(
                f"💥 Error in LiveKit publisher ({self.node_id}): {e}",
                exc_info=True
            )
            raise
        
    async def disconnect(self) -> None:
        """Disconnect from LiveKit room"""
        logger.debug(f"({self.node_id}) Disconnecting from LiveKit room...")
        if self.room:
            await self.room.disconnect()
            self.room = None
        logger.debug(f"({self.node_id}) 🏁 Disconnected from LiveKit room")
        
    async def send_data(self, data: Any) -> None:
        """
        For each specific publisher node, the send_data method should be implemented.
        """
        pass
