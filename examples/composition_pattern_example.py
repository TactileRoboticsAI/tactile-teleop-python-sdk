"""
Example demonstrating the composition pattern for control providers and subscriber nodes.

This shows how to properly wire up a control provider (business logic) with a 
subscriber node (transport layer) using composition instead of inheritance.
"""

import asyncio
import logging

from tactile_teleop_sdk.config import TeleopConfig
from tactile_teleop_sdk.control_providers.pg_vr_controller import (
    ParallelGripperVRController,
    ArmParallelGripperGoal,
)
from tactile_teleop_sdk.subscriber_node.base import create_subscriber
from tactile_teleop_sdk.subscriber_node.livekit import LivekitSubscriberConnectionConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s"
)


async def main():
    # 1. Create configuration
    config = TeleopConfig(
        api_key="your-api-key",
        protocol="livekit",
        gripper_type="parallel"
    )
    
    # 2. Create control provider (business logic layer)
    controller = ParallelGripperVRController(
        config=config,
        component_ids=["left", "right"]
    )
    
    # 3. Create connection config for transport layer
    connection_config = LivekitSubscriberConnectionConfig(
        protocol="livekit",
        room_name="robot-room",
        livekit_url="wss://your-livekit-server.com",
        token="your-livekit-token",
        participant_identity="robot-controller"
    )
    
    # 4. Create subscriber node (transport layer) using factory
    subscriber = create_subscriber(
        node_id="vr-controller-subscriber",
        connection_config=connection_config
    )
    
    # 5. COMPOSITION PATTERN: Wire them together via callback
    subscriber.register_data_callback(controller.process_vr_data)
    
    # 6. Connect to transport layer
    await subscriber.connect()
    
    try:
        # 7. Main control loop - poll for robot goals
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
        # 8. Clean shutdown
        await subscriber.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

