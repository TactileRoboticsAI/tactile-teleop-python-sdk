import logging

import numpy as np
from livekit import rtc

from tactile_teleop_sdk.camera.vr_camera_streamer.base import (
    BaseVRCameraStreamer,
    CameraSettings,
)
from tactile_teleop_sdk.publisher_node.livekit import LivekitPublisherConnectionConfig

logger = logging.getLogger(__name__)


class LivekitVRCameraStreamer(BaseVRCameraStreamer):
    """LiveKit implementation of VR camera streamer"""
    
    def __init__(
        self,
        camera_settings: CameraSettings,
        connection_config: LivekitPublisherConnectionConfig,
        track_name: str = "robot0-birds-eye",
    ):
        super().__init__(camera_settings, connection_config)
        self.connection_config: LivekitPublisherConnectionConfig = connection_config
        self.track_name = track_name
        
        # Stereo width (2x for side-by-side)
        self.stereo_width = camera_settings.width * 2
        self.height = camera_settings.height
        
        # Initialize LiveKit video source and track
        self._init_video_track()
    
    
    def _init_video_track(self) -> None:
        """Initialize LiveKit VideoSource and LocalVideoTrack"""
        self.source = rtc.VideoSource(self.stereo_width, self.height)
        self.track = rtc.LocalVideoTrack.create_video_track(self.track_name, self.source)
        self.options = rtc.TrackPublishOptions(
            source=rtc.TrackSource.SOURCE_CAMERA,
            simulcast=False,
            video_encoding=rtc.VideoEncoding(
                max_framerate=self.camera_settings.max_framerate,
                max_bitrate=self.camera_settings.max_bitrate,
            ),
            video_codec=rtc.VideoCodec.H264,
        )
        
        # Inject track into connection config for publisher
        self.connection_config.track = self.track
        self.connection_config.track_publish_options = self.options
    
    
    async def send_stereo_frame(self, frame: np.ndarray) -> None:
        """Send pre-concatenated stereo frame"""
        await self._send_frame(frame)
    
    
    async def _send_frame(self, frame: np.ndarray) -> None:
        """Internal method to capture and send frame to VideoSource"""
        frame_bytes = frame.tobytes()
        video_frame = rtc.VideoFrame(
            self.stereo_width,
            self.height,
            rtc.VideoBufferType.RGB24,
            frame_bytes,
        )
        self.source.capture_frame(video_frame)
