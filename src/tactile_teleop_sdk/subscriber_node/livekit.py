from ast import Dict
import asyncio
import json
import logging
from abc import abstractmethod

from livekit import rtc

from tactile_teleop_sdk.subscriber_node.base import (
    BaseSubscriberNode,
    BaseConnectionConfig,
    register_protocol,
)

logger = logging.getLogger(__name__)


class LivekitSubscriberConnectionConfig(BaseConnectionConfig):
    protocol: str = "livekit"
    livekit_url: str
    token: str
    participant_identity: str


@register_protocol("livekit")
class LivekitSubscriberNode(BaseSubscriberNode):
    """LiveKit implementation of subscriber node"""
    
    def __init__(self, node_id: str, connection_config: LivekitSubscriberConnectionConfig):
        super().__init__(node_id, connection_config)
        self.connection_config: LivekitSubscriberConnectionConfig = connection_config
        self.room: rtc.Room | None = None
        self._data_tasks: set[asyncio.Task] = set()
        
    @abstractmethod
    async def _process_data(self, data: Dict):
        """Process incoming data."""
        pass

    async def _handle_data_packet(self, packet: rtc.DataPacket) -> None:
        """Handle data packet coming from LiveKit."""
        try:
            payload = json.loads(packet.data.decode("utf-8"))
            await self._process_data(payload)
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {packet.data}")
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
        def on_track_published(publication, participant):
            logger.debug(f"📹 Track published by {participant.identity}: {publication.kind}")

        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            task = asyncio.create_task(self._handle_data_packet(data))

            # Keep track of outstanding packet-processing tasks so we can cancel them on shutdown
            self._data_tasks.add(task)
            task.add_done_callback(self._data_tasks.discard)
            
        try:
            await self.room.connect(
                self.connection_config.livekit_url,
                self.connection_config.token
            )
            
            # Log connection state
            logger.debug(f"✅ Connected to LiveKit room {self.connection_config.room_name} as node {self.node_id}")
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
    
