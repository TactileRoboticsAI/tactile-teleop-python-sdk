import asyncio

import numpy as np

from tactile_teleop_sdk import TactileAPI

CAMERA_WIDTH = 580
CAMERA_HEIGHT = 480


async def main():
    # Initialize the API
    api = TactileAPI(api_key="your_key_here")

    # Connect VR controllers
    await api.connect_vr_controller()

    # Connect camera streamer
    await api.connect_camera_streamer(CAMERA_HEIGHT, CAMERA_WIDTH)

    try:
        while True:
            # Get VR controller input
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Process controller data
            if left_goal.relative_transform is not None:
                print(f"Left arm transform: {left_goal.relative_transform}")

            if right_goal.relative_transform is not None:
                print(f"Left arm transform: {left_goal.relative_transform}")

            # Send camera frame (example with dummy data)
            dummy_frame = np.random.randint(0, 255, (480, 580, 3), dtype=np.uint8)
            await api.send_single_frame(dummy_frame)

            await asyncio.sleep(0.01)  # 100Hz loop

    finally:
        # Clean up connections
        await api.disconnect_vr_controller()
        await api.disconnect_camera_streamer()


if __name__ == "__main__":
    asyncio.run(main())
