import asyncio
import numpy as np
from tactile_teleop_sdk.api import TactileAPI
from tactile_teleop_sdk.config import TactileConfig

async def main():
    # Initialize API with config from environment variables
    config = TactileConfig.load()
    api = TactileAPI(config)

    # Connect and wait for operator
    await api.wait_for_operator(timeout=300.0)

    # Connect VR controller
    await api.connect_controller(type="parallel_gripper_vr_controller", robot_components=["left", "right"])

    # Connect camera streamer with custom resolution
    await api.connect_camera(
        camera_name="main_camera",
        height=480,
        width=640,
        max_framerate=30,
        max_bitrate=3_000_000
    )    
    try:
        # Main control loop
        while True:
            # Get control goals for robot components
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Execute robot control with received goals
            # ... your robot control logic here ...

            # Send camera frames back to operator
            left_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            right_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            await api.send_stereo_frame(left_frame, right_frame, camera_id="main_camera")

            await asyncio.sleep(0.01)  # 100Hz control loop

    finally:
        await api.diswait_for_operator()

if __name__ == "__main__":
    asyncio.run(main())
