import logging

import numpy as np
from livekit import rtc

from tactile_teleop_sdk.camera.camera_publisher.base import (
    BaseCameraPublisher,
    CameraSettings,
    register_camera_publisher,
)
from tactile_teleop_sdk.publisher_node.livekit import LivekitPublisherAuthConfig

logger = logging.getLogger(__name__)


@register_camera_publisher("livekit_vr")
class LivekitVRCameraStreamer(BaseCameraPublisher):
    """LiveKit implementation of VR camera streamer"""
    
    def __init__(
        self,
        camera_settings: CameraSettings,
        protocol_auth_config: LivekitPublisherAuthConfig,
    ):
        self.camera_settings = camera_settings
        self.track_name = "robot0-birds-eye"
        
        # Stereo width (2x for side-by-side)
        self.stereo_width = camera_settings.width * 2
        self.height = camera_settings.height
        
        # Initialize LiveKit video source and track
        self._init_video_track()
        
        super().__init__(camera_settings, protocol_auth_config)
    
    async def connect(self, **publisher_kwargs) -> None:
        """Initialize publisher with track and establish connection"""
        await super().connect(track=self.track, track_publish_options=self.options, **publisher_kwargs)
    
    
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
