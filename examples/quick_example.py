import asyncio

import numpy as np

from tactile_teleop_sdk import TactileAPI, TactileConfig

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


async def main():
    # Initialize the API with config from environment
    config = TactileConfig.from_env()
    api = TactileAPI(config)
    
    # Connect to robot and wait for operator
    await api.connect_robot()

    # Connect VR controller
    await api.connect_controller(type="parallel_gripper_vr_controller", robot_components=["left", "right"])

    # Connect camera streamer with specified resolution
    await api.connect_camera(
        camera_name="main_camera",
        height=CAMERA_HEIGHT,
        width=CAMERA_WIDTH
    )

    try:
        while True:
            # Get VR controller input
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Your robot control logic here
            # ...

            # Send camera frame (example with dummy data)
            dummy_frame = np.random.randint(0, 255, (CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
            await api.send_single_frame(dummy_frame, camera_id="main_camera")

            await asyncio.sleep(0.01)

    finally:
        await api.disconnect_robot()

if __name__ == "__main__":
    asyncio.run(main())
