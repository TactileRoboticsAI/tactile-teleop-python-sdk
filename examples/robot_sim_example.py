import asyncio
import numpy as np
from tactile_teleop_sdk.api import TactileAPI
from tactile_teleop_sdk.config import TactileConfig

async def main():
    """
    Example matching the user's workflow with robot simulation and viewer.
    Demonstrates dynamic camera configuration based on viewer resolution.
    """

    config = TactileConfig.from_env()
    api = TactileAPI(config)

    # Connect to robot server and wait for operator
    await api.wait_for_operator()

    # Viewer setup (simulated - replace with your actual viewer)
    # viewer = newton.viewer.ViewerGL(headless=False)
    # fb_w, fb_h = viewer.renderer.window.get_framebuffer_size()
    fb_w, fb_h = 1920, 1080  # Example framebuffer size

    # Connect VR controls
    await api.connect_controller(type="parallel_gripper_vr_controller", robot_components=["left", "right"])

    # Connect camera streamer with viewer resolution
    await api.connect_camera(
        camera_name="camera_0",
        height=fb_h,
        width=fb_w,
        max_framerate=60,
        max_bitrate=5_000_000
    )

    try:
        while True:
            # Get VR controller goals
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Apply goals to robot
            # robot.set_left_target(left_goal)
            # robot.set_right_target(right_goal)

            # Render scene and send to operator
            # frame = viewer.render()
            frame = np.random.randint(0, 255, (fb_h, fb_w, 3), dtype=np.uint8)
            await api.send_single_frame(frame, camera_id="camera_0")

            await asyncio.sleep(0.01)

    finally:
        await api.diswait_for_operator()

if __name__ == "__main__":
    asyncio.run(main())
