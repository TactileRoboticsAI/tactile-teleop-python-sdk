# Tactile Teleop Python SDK

## Overview

The Tactile Teleop Python SDK enables seamless integration between robotic manipulation systems and VR-based teleoperation. It provides:

- **VR Controller Input**: Real-time low-latency VR controller data for robotic arm control  
- **Camera Streaming**: Stereo and mono camera feed streaming to VR headsets  
- **Easy Setup**: Connect your robot in minutes - just generate an API key at [teleop.tactilerobotics.ai](https://teleop.tactilerobotics.ai), plug it into the Python SDK, and access your robot directly from the VR headset’s native browser.
## Quickstart

### Conda Installation

```bash
git clone git@github.com:TactileRoboticsAI/tactile-teleop-python-sdk.git
cd tactile-teleop-python-sdk
conda create -n tactile python=3.10
conda activate tactile
pip install -e .
```

### UV Installation

```bash
git clone git@github.com:TactileRoboticsAI/tactile-teleop-python-sdk.git
cd tactile-teleop-python-sdk
uv sync
```

### Create API key

Visit [teleop.tactilerobotics.ai](https://teleop.tactilerobotics.ai), register and create a new robot. Save the automatically generated API key.

### Minimal Example

```python
import asyncio
import os

import numpy as np

from tactile_teleop_sdk import TactileAPI
from tactile_teleop_sdk.utils.visualizer import TransformVisualizer

CAMERA_WIDTH = 580
CAMERA_HEIGHT = 480
API_KEY = ""  # NOTE: Replace with your robot API key from https://teleop.tactilerobotics.ai


async def main():
    # Initialize the API
    api = TactileAPI(api_key=API_KEY)

    # Initialize visualizer (will open browser automatically)
    visualizer = TransformVisualizer()

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
                visualizer.update_visualization(
                    left_transform=left_goal.relative_transform,
                    right_transform=right_goal.relative_transform,
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
```
### On the VR Headset

Go to the Browser of your VR headset and visit [teleop.tactilerobotics.ai](https://teleop.tactilerobotics.ai). Login, and press start VR Control on the robot.

#### Controller Mapping

- **Grip Button**: Sets reference frame when first pressed, enables position control when held
- **Trigger Button**: Controls gripper (pressed = open, released = closed)
- **Reset Button (X/A)**: Trigger to reset arm to initial position
- **Position Tracking**: Controller movement translates to arm movement when grip is held