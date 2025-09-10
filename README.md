# Tactile Teleop Python SDK

## Overview

The Tactile Teleop Python SDK enables seamless integration between robotic systems and VR-based teleoperation. It provides:

- **VR Controller Input**: Real-time VR controller data for robotic arm control
- **Camera Streaming**: Stereo and mono camera feed streaming to VR headsets
- **LiveKit Integration**: Secure, low-latency communication via LiveKit
- **Easy Authentication**: Simple API key-based authentication with Tactile Robotics backend

### Conda Installation

```bash
git clone <repository-url>
cd tactile-teleop-python-sdk
conda create -n tactile python=3.10
conda activate
pip install -e .
```

### UV Installation

```bash
git clone <repository-url>
cd tactile-teleop-python-sdk
uv sync
```

## Quick Start

```python
import asyncio
import numpy as np
from tactile_teleop_sdk import TactileAPI

async def main():
    # Initialize the API
    api = TactileAPI(api_key="your-api-key", robot_name="your-robot")
    
    # Connect VR controllers
    await api.connect_vr_controller()
    
    # Connect camera streamer
    await api.connect_camera_streamer()
    
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
            dummy_frame = np.zeros((480, 580, 3), dtype=np.uint8)
            await api.send_single_frame(dummy_frame)
            
            await asyncio.sleep(0.01)  # 100Hz loop
            
    finally:
        # Clean up connections
        await api.disconnect_vr_controller()
        await api.disconnect_camera_streamer()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### TactileAPI

The main class for interacting with the Tactile Teleop system.

#### Constructor

```python
TactileAPI(api_key: str, robot_name: str)
```

- `api_key`: Your Robot API key
- `robot_name`: Your robot name from the dashboard

#### Controller Mapping

- **Grip Button**: Sets reference frame when first pressed, enables position control when held
- **Trigger Button**: Controls gripper (pressed = open, released = closed)
- **Reset Button (X/A)**: Resets arm to initial position
- **Position Tracking**: Controller movement translates to arm movement when grip is held

## Camera Configuration

Configure camera settings through the `CameraConfig` class:

```python
from tactile_teleop_sdk.config import CameraConfig, TactileTeleopConfig

# Custom camera configuration
camera_config = CameraConfig(
    stereo_camera=True,  # Set to True for stereo cameras
    width=640,           # Camera width
    height=480           # Camera height
)

# Apply configuration (modify TactileAPI initialization as needed)
```

## Frame Formats

### Stereo Frames
- **Input**: `np.ndarray` with shape `(height, 2*width, 3)`
- **Format**: Horizontally concatenated left and right images
- **Data Type**: `uint8`
- **Color Space**: RGB

### Mono Frames
- **Input**: `np.ndarray` with shape `(height, width, 3)`
- **Format**: Single camera image (automatically duplicated for stereo display)
- **Data Type**: `uint8`
- **Color Space**: RGB