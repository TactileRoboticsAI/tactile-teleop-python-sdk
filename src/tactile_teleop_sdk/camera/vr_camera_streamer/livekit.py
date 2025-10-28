import logging
from typing import Optional

import numpy as np
from livekit import rtc

logger = logging.getLogger(__name__)


class LivekitCameraStreamer:
    def __init__(
        self,
        height: int,
        width: int,
        max_framerate: int = 30,
        max_bitrate: int = 3_000_000,
    ):
        self.width = width * 2
        self.height = height
        
        # Livekit Specific
        self.source = rtc.VideoSource(self.width, self.height)
        self.track = rtc.LocalVideoTrack.create_video_track("robot0-birds-eye", self.source)
        self.room: Optional[rtc.Room] = None

        self.options = rtc.TrackPublishOptions(
            source=rtc.TrackSource.SOURCE_CAMERA,
            simulcast=False,
            video_encoding=rtc.VideoEncoding(
                max_framerate=max_framerate,
                max_bitrate=max_bitrate,
            ),
            video_codec=rtc.VideoCodec.H264,
        )
    
    async def _publish_track(self, room: rtc.Room):
        try:
            await room.local_participant.publish_track(self.track, self.options)
            logger.info("(CameraStreamer) Published video track successfully")
        except Exception as e:
            logger.error(f"Failed to publish video track: {e}", exc_info=True)
            raise

    async def connect(self, room_name: str, participant_name: str, token: str, livekit_url: str) -> None:
        self.room = rtc.Room()

        @self.room.on("participant_connected")
        def on_participant_connected(participant):
            print(f"🟢 Node connected: {participant.identity}")

        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            print(f"🔴 Node disconnected: {participant.identity}")

        @self.room.on("track_published")
        def on_track_published(publication, participant):
            print(f"📹 Track published by {participant.identity}: {publication.kind}")

        try:
            await self.room.connect(livekit_url, token)
            
            # Log connection state
            logger.info(f"✅ Connected to LiveKit room {room_name} as node {participant_name}")
            logger.info(f"🔍 Room connection state: {self.room.connection_state}")
            logger.info(f"🔍 Local node (should = {participant_name}): {self.room.local_participant.identity}")
            logger.info(f"📊 Remote room nodes: {len(self.room.remote_participants)}")
            for participant in self.room.remote_participants.values():
                logger.info(f"  - {participant.identity} ({participant.sid})")

            await self._publish_track(self.room)

        except KeyboardInterrupt:
            logger.info("(CameraStreamer) ⌨️  KeyboardInterrupt, shutting down")
        except Exception as e:
            logger.error(f"💥 Error in camera streamer node connection process: {e}", exc_info=True)

    async def disconnect(self, timeout: float = 5.0) -> None:
        logger.info("(CameraStreamer) Disconnecting from LiveKit room...")

        if hasattr(self, "room") and self.room:
            await self.room.disconnect()
        logger.info("(CameraStreamer) 🏁 Node disconnected from LiveKit room")

    async def send_single_frame(self, frame: np.ndarray) -> None:
        concatenated_frame = np.concatenate([frame, frame], axis=1)

        frame_bytes = concatenated_frame.tobytes()
        video_frame = rtc.VideoFrame(
            self.width,
            self.height,
            rtc.VideoBufferType.RGB24,
            frame_bytes,
        )
        self.source.capture_frame(video_frame)

    async def send_stereo_frame(self, frame: np.ndarray) -> None:
        frame_bytes = frame.tobytes()
        video_frame = rtc.VideoFrame(
            self.width,
            self.height,
            rtc.VideoBufferType.RGB24,
            frame_bytes,
        )
        self.source.capture_frame(video_frame)


