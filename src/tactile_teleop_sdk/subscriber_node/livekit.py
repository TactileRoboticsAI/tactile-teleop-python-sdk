import asyncio
import json
import logging
from typing import List
from livekit import rtc

from tactile_teleop_sdk.subscriber_node.base import (
    BaseSubscriberNode,
    register_protocol,
)
from tactile_teleop_sdk.protocol_auth import (
    BaseProtocolAuthConfig,
    register_protocol_auth_config,
)

logger = logging.getLogger(__name__)


@register_protocol_auth_config("livekit")
class LivekitSubscriberAuthConfig(BaseProtocolAuthConfig):
    protocol: str = "livekit"
    server_url: str
    token: str


@register_protocol("livekit")
class LivekitSubscriberNode(BaseSubscriberNode):
    """LiveKit implementation of subscriber node"""
    
    def __init__(self, node_id: str, protocol_auth_config: LivekitSubscriberAuthConfig, subscribe_sources: List[str]):
        super().__init__(node_id, protocol_auth_config, subscribe_sources=subscribe_sources)
        self.protocol_auth_config: LivekitSubscriberAuthConfig = protocol_auth_config
        self.room: rtc.Room | None = None
        self.subscribe_sources = subscribe_sources
        self._data_tasks: set[asyncio.Task] = set()

    async def _handle_data_packet(self, packet: rtc.DataPacket) -> None:
        """Handle data packet coming from LiveKit."""
        try:
            payload = json.loads(packet.data.decode("utf-8"))
            if self._data_callback:
                await self._data_callback(payload)
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {packet.data.decode('utf-8', errors='replace')}")
            return
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return
    
    async def connect(self) -> None:
        """Connect to LiveKit room as a subscriber"""
        self.room = rtc.Room()

        @self.room.on("participant_connected")
        def on_participant_connected(participant):
            logger.debug(f"🟢 Node connected: {participant.identity}")

        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            logger.debug(f"🔴 Node disconnected: {participant.identity}")

        @self.room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            logger.debug(f"📹 Track published by {participant.identity}: {publication.kind}")
            if participant.identity in self.subscribe_sources:
                logger.debug(f"Subscribing to new track from {participant.identity}: {publication.kind}")
                publication.set_subscribed(True)
            else:
                logger.debug(f"Not subscribing to track from {participant.identity}: {publication.kind}")

        # Subscribe to tracks from participants already in the room
        for participant in self.room.remote_participants.values():
            if participant.identity in self.subscribe_sources:
                for publication in participant.track_publications.values():
                    logger.debug(f"Subscribing to existing track from {participant.identity}: {publication.kind}")
                    publication.set_subscribed(True) 

        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            task = asyncio.create_task(self._handle_data_packet(data))

            # Keep track of outstanding packet-processing tasks so we can cancel them on shutdown
            self._data_tasks.add(task)
            task.add_done_callback(self._data_tasks.discard)
            
        try:
            await self.room.connect(
                self.protocol_auth_config.server_url,
                self.protocol_auth_config.token,
                options=rtc.RoomOptions(auto_subscribe=False)
            )
            
            # Log connection state
            logger.debug(f"✅ Connected to LiveKit room {self.protocol_auth_config.room_name} as node {self.node_id}")
            logger.debug(f"🔍 Room connection state: {self.room.connection_state}")
            logger.debug(f"🔍 Local node (should = {self.node_id}): {self.room.local_participant.identity}")
            logger.debug(f"📊 Remote room nodes: {len(self.room.remote_participants)}")
            for participant in self.room.remote_participants.values():
                logger.debug(f"  - {participant.identity} ({participant.sid})")

        except Exception as e:
            logger.error(f"💥 Failed to connect to LiveKit: {e}", exc_info=True)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from LiveKit room"""
        logger.debug(f"({self.node_id}) Disconnecting from LiveKit room...")
        
        # Cancel and wait for any in-flight packet processing tasks
        for task in list(self._data_tasks):
            task.cancel()
        if self._data_tasks:
            await asyncio.gather(*self._data_tasks, return_exceptions=True)
        self._data_tasks.clear()
        
        if self.room:
            await self.room.disconnect()
            self.room = None
            
        logger.debug(f"({self.node_id}) 🏁 Disconnected from LiveKit room")
    
