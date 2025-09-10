import asyncio

import numpy as np

from tactile_teleop_sdk import TactileAPI
from tactile_teleop_sdk.utils.visualizer import create_visualizer

CAMERA_WIDTH = 580
CAMERA_HEIGHT = 480


async def main():
    # Initialize the API
    api = TactileAPI(api_key="tr_ItBlqHILUi4vIyhRtgzTh-47yZZaMqz2uc_-QranDdA")

    # Initialize visualizer (will open browser automatically)
    visualizer = create_visualizer()
    if visualizer:
        print("Visualization available at: http://localhost:7000")

    # Connect VR controllers
    await api.connect_vr_controller()

    # Connect camera streamer
    await api.connect_camera_streamer(CAMERA_HEIGHT, CAMERA_WIDTH)

    try:
        while True:
            # Get VR controller input
            left_goal = await api.get_controller_goal("left")
            right_goal = await api.get_controller_goal("right")

            # Visualize VR controller relative transforms
            if visualizer:
                visualizer.update_vr_controllers(
                    left_transform=left_goal.relative_transform,
                    right_transform=right_goal.relative_transform,
                    scale=0.15,
                )

            # Send camera frame (example with dummy data)
            dummy_frame = np.random.randint(0, 255, (CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
            await api.send_single_frame(dummy_frame)

            await asyncio.sleep(0.01)

    finally:
        await api.disconnect_vr_controller()
        await api.disconnect_camera_streamer()

        if visualizer:
            visualizer.close()


if __name__ == "__main__":
    asyncio.run(main())
