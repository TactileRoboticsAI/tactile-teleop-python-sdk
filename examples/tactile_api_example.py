import asyncio
import numpy as np
from tactile_teleop_sdk.api import TactileAPI
from tactile_teleop_sdk.config import TactileConfig

async def main():
    # Initialize API with config from environment variables
    config = TactileConfig.from_env()
    api = TactileAPI(config)
    
    # Connect and wait for operator
    await api.connect_robot(timeout=300.0)
    
    try:
        # Main control loop
        while True:
            # Get control goals for robot components
            left_arm_goal = await api.get_controller_goal("left_arm")
            right_arm_goal = await api.get_controller_goal("right_arm")
            
            # Execute robot control with received goals
            # ... your robot control logic here ...
            
            # Send camera frames back to operator
            left_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            right_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            await api.send_stereo_frame(left_frame, right_frame)
            
            # Optional: Custom data streams
            telemetry_pub = await api.get_publisher("telemetry")
            await telemetry_pub.send_data({"battery": 85, "temp": 42.5})
            
            sensor_sub = await api.get_subscriber("custom_sensor")
            sensor_data = sensor_sub.get_latest_data() # type: ignore
            
            await asyncio.sleep(0.01)  # 100Hz control loop
            
    finally:
        await api.disconnect_robot()

if __name__ == "__main__":
    asyncio.run(main())

