import asyncio
import numpy as np
from tactile_teleop_sdk.api import TactileAPI
from tactile_teleop_sdk.config import TactileConfig

async def main():
    """
    Example showing multiple camera streamers for VR headset views.
    This demonstrates connecting 3 different camera angles simultaneously.
    """
    config = TactileConfig.from_env()
    api = TactileAPI(config)

    await api.wait_for_operator(timeout=300.0)

    # Connect VR controller
    await api.connect_controller(type="parallel_gripper_vr_controller", robot_components=["left", "right"])

    # Connect multiple camera streamers for different viewpoints
    await api.connect_camera(
        camera_name="front_camera",
        height=1080,
        width=1920,
        max_framerate=60,
        max_bitrate=5_000_000
    )

    await api.connect_camera(
        camera_name="wrist_camera_left",
        height=480,
        width=640,
        max_framerate=30
    )

    await api.connect_camera(
        camera_name="wrist_camera_right",
        height=480,
        width=640,
        max_framerate=30
    )

    try:
        while True:
            # Get VR controller input
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Your robot control logic here
            # ...

            # Send frames from different cameras
            front_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
            await api.send_single_frame(front_frame, camera_id="front_camera")

            wrist_left_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            await api.send_single_frame(wrist_left_frame, camera_id="wrist_camera_left")

            wrist_right_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            await api.send_single_frame(wrist_right_frame, camera_id="wrist_camera_right")

            await asyncio.sleep(0.01)

    finally:
        await api.diswait_for_operator()

if __name__ == "__main__":
    asyncio.run(main())
