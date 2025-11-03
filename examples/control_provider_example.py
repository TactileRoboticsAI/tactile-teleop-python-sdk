"""
Example demonstrating the Bridge Pattern for control providers.

This shows how control providers (business logic) integrate with
transport layer (subscriber nodes) through the Bridge Pattern.

The connection configuration is explicitly provided, typically read
from a config file or API response in your application.
"""

import asyncio
import logging

from tactile_teleop_sdk.config import TeleopConfig
from tactile_teleop_sdk.control_providers.pg_vr_controller import (
    ParallelGripperVRController,
    ArmParallelGripperGoal,
)
from tactile_teleop_sdk.subscriber_node.livekit import LivekitSubscriberAuthConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s"
)


async def basic_example():
    """Basic usage with explicit connection config"""
    
    # 1. Create configuration
    config = TeleopConfig(
        api_key="your-api-key",
        protocol="livekit",
        gripper_type="parallel"
    )
    
    # 2. Create connection config (typically from config file or API)
    connection_config = LivekitSubscriberAuthConfig(
        protocol="livekit",
        room_name="robot-room",
        livekit_url="wss://your-livekit-server.com",
        token="your-livekit-token",
        participant_identity="robot-controller"
    )
    
    # 3. Create control provider with explicit connection config
    controller = ParallelGripperVRController(
        config=config,
        component_ids=["left", "right"],
        connection_config=connection_config
    )
    
    # 4. Connect to transport layer
    await controller.connect()
    
    try:
        # 5. Main control loop - poll for robot goals
        while True:
            # Get control goals from the controller
            left_goal: ArmParallelGripperGoal = controller.get_control_goal("left")
            right_goal: ArmParallelGripperGoal = controller.get_control_goal("right")
            
            # Use the goals to control your robot
            if left_goal.relative_transform is not None:
                print(f"Left arm transform: {left_goal.relative_transform}")
            if left_goal.gripper_closed is not None:
                print(f"Left gripper: {'CLOSED' if left_goal.gripper_closed else 'OPEN'}")
            
            if right_goal.relative_transform is not None:
                print(f"Right arm transform: {right_goal.relative_transform}")
            if right_goal.gripper_closed is not None:
                print(f"Right gripper: {'CLOSED' if right_goal.gripper_closed else 'OPEN'}")
            
            await asyncio.sleep(0.01)
            
    finally:
        # 6. Clean shutdown
        await controller.disconnect()


async def main():
    """Run the example"""
    await basic_example()


if __name__ == "__main__":
    asyncio.run(main())

