import logging
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum

import numpy as np
from pydantic import ConfigDict

from tactile_teleop_sdk.control_subscribers.base import (
    BaseControlGoal, 
    BaseControlSubscriber, 
    BaseOperatorEvent,
    register_control_subscriber,
)
from tactile_teleop_sdk.subscriber_node.base import BaseProtocolAuthConfig
from tactile_teleop_sdk.utils.geometry import pose2transform

logger = logging.getLogger(__name__)


class TactileVRControllerEventType(Enum):
    """Control goal types."""

    IDLE = "idle"  # No button on vr controller pressed
    GRIP_ACTIVE_INIT = "grip_active_init"  # Grip button pressed first time
    GRIP_ACTIVE = "grip_active"  # Grip button held -> moving the robot arms
    GRIP_RELEASE = "grip_release"  # Grip button released
    TRIGGER_ACTIVE = "trigger_active"  # Trigger button pressed
    TRIGGER_RELEASE = "trigger_release"  # Trigger button released
    RESET_BUTTON_RELEASE = "reset_button_release"  # Reset button released


@dataclass
class VRControllerState:
    """High frequency streaming state from VR controller.
    
    Mirrors the data structure sent by the frontend in each tick() call.
    Used to track controller state between incoming data packets.
    """
    hand: str = "right"
    position: np.ndarray | None = None  # 3D position vector [x, y, z]
    quaternion: np.ndarray | None = None  # Orientation quaternion [x, y, z, w]
    grip_active: bool = False
    trigger_active: bool = False
    button_down: bool = False  # X button (left) or A button (right)
    
    # Computed state for grip tracking
    origin_transform: np.ndarray | None = None  # 4x4 transform when grip activated

    def reset_grip(self):
        """Reset grip state but preserve trigger state."""
        self.grip_active = False
        self.origin_transform = None


@dataclass
class VRControllerEvent(BaseOperatorEvent):
    """Lower frequency control events coming from the VR Controllers."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    component_id: str = "right"
    event_type: TactileVRControllerEventType = TactileVRControllerEventType.IDLE
    origin_transform: Optional[np.ndarray] = None
    target_transform: Optional[np.ndarray] = None
    gripper_closed: Optional[bool] = None
    
    
@dataclass
class ParallelGripperControlGoal(BaseControlGoal):
    """Robot control goal for a parallel gripper arm, exposed to the user with the API"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    component_id: str = "right"
    relative_transform: Optional[np.ndarray] = None
    gripper_closed: Optional[bool] = None
    reset_to_init: bool = False
    reset_reference: bool = False
    

@register_control_subscriber("ParallelGripperVRController")
class ParallelGripperVRController(BaseControlSubscriber):
    """Control provider for VR controllers with parallel grippers.
    
    Processes VR controller data and generates robot control goals.
    Inherits from BaseControlSubscriber which handles transport layer via Bridge pattern.
    
    Usage:
        # Create connection config (typically from API/config file)
        connection_config = LivekitSubscriberAuthConfig(
            protocol="livekit",
            room_name="robot-room",
            livekit_url="wss://server.com",
            token="token",
            participant_identity="robot-1"
        )
        
        # Create controller with explicit connection config
        controller = ParallelGripperVRController(
            config=TeleopConfig(api_key="your-key"),
            component_ids=["left", "right"],
            connection_config=connection_config
        )
        await controller.connect()
    """
    
    def __init__(
        self, 
        component_ids: List[str],
        connection_config: BaseProtocolAuthConfig,
        node_id: Optional[str] = None
    ):
        super().__init__(component_ids, connection_config, node_id)
        self.left_controller = VRControllerState(hand="left")
        self.right_controller = VRControllerState(hand="right")
        self.left_gripper_closed = True
        self.right_gripper_closed = True
        
    # Implementation of the abstract method of the BaseControlSubscriber
    def _process_operator_data_queue(self, operator_data_queue: list[VRControllerEvent], component_id: str) -> ParallelGripperControlGoal:
        
        robot_goal = ParallelGripperControlGoal(component_id=component_id)
        event_data = VRControllerEvent(component_id=component_id)
        last_active_grip_data: VRControllerEvent | None = None
        
        # Catch Events from the stream of high frequency operator data
        for operator_data in operator_data_queue:
            if operator_data.component_id != component_id:
                continue
            if operator_data.event_type == TactileVRControllerEventType.GRIP_ACTIVE_INIT:
                event_data.origin_transform = operator_data.target_transform
                robot_goal.reset_reference = True
            elif operator_data.event_type == TactileVRControllerEventType.GRIP_ACTIVE:
                last_active_grip_data = operator_data
            elif operator_data.event_type == TactileVRControllerEventType.GRIP_RELEASE:
                event_data.target_transform = None
            elif operator_data.event_type == TactileVRControllerEventType.TRIGGER_ACTIVE:
                if component_id == "left":
                    self.left_gripper_closed = False
                elif component_id == "right":
                    self.right_gripper_closed = False
            elif operator_data.event_type == TactileVRControllerEventType.TRIGGER_RELEASE:
                if component_id == "left":
                    self.left_gripper_closed = True
                elif component_id == "right":
                    self.right_gripper_closed = True
            elif operator_data.event_type == TactileVRControllerEventType.RESET_BUTTON_RELEASE:
                # NOTE: When pressing grip right after reset, this may get overwritten and not actually reset
                event_data.origin_transform = None
                event_data.target_transform = None
                robot_goal.reset_to_init = True
            else:
                raise ValueError(f"Unknown event type: {operator_data.event_type}")

        if last_active_grip_data is not None:
            vr_reference_transform = last_active_grip_data.origin_transform 
            vr_target_transform = last_active_grip_data.target_transform
            
            if vr_reference_transform is not None and vr_target_transform is not None:
                # Compute relative transform from reference to target
                relative_transform = np.linalg.inv(vr_reference_transform) @ vr_target_transform

                # Coordinate transform to global VR frame
                transformation_matrix = np.eye(4)
                transformation_matrix[:3, :3] = vr_reference_transform[:3, :3]
                relative_transform = transformation_matrix @ (relative_transform @ np.linalg.inv(transformation_matrix))
                
                # Store the relative transform in the control goal
                robot_goal.relative_transform = relative_transform

        # Store the gripper state in the control goal
        robot_goal.gripper_closed = self.left_gripper_closed if component_id == "left" else self.right_gripper_closed
        return robot_goal
    
    async def _handle_incoming_data(self, data: Dict):
        """Handle incoming VR controller data from transport layer.
        
        Template method implementation - automatically called by BaseControlSubscriber.
        """
        left_data = data.get("leftController", {})
        right_data = data.get("rightController", {})

        left_active = left_data.get("gripActive", False) or left_data.get("trigger", 0) > 0.5
        right_active = right_data.get("gripActive", False) or right_data.get("trigger", 0) > 0.5

        if left_active or right_active:
            logger.info(
                f"(VRControllerInputProvider) 🎮 Controller ACTIVE - Left: grip={left_data.get('gripActive')}, trigger={left_data.get('trigger'):.1f} | Right: grip={right_data.get('gripActive')}, trigger={right_data.get('trigger'):.1f}"
            )
        else:
            logger.debug("(VRControllerInputProvider) 🎮 Controllers idle")

        if "leftController" in data and "rightController" in data:
            left_data = data["leftController"]
            right_data = data["rightController"]

            # Process left controller
            if left_data.get("position") and (left_data.get("gripActive", False) or left_data.get("trigger", 0) > 0.5):
                await self._process_single_controller("left", left_data)
            elif not left_data.get("gripActive", False) and self.left_controller.grip_active:
                await self._handle_grip_release("left")

            # Process right controller
            if right_data.get("position") and (
                right_data.get("gripActive", False) or right_data.get("trigger", 0) > 0.5
            ):
                await self._process_single_controller("right", right_data)
            elif not right_data.get("gripActive", False) and self.right_controller.grip_active:
                await self._handle_grip_release("right")

            return

        hand: str | None = data.get("hand")
        
        if hand is None:
            return

        if data.get("gripReleased"):
            await self._handle_grip_release(hand)
            return

        if data.get("triggerReleased"):
            await self._handle_trigger_release(hand)
            return

        if data.get("resetEvent"):
            await self._handle_reset_button_release(hand)
            return

    async def _process_single_controller(self, hand: str, data: Dict):
        """Process streaming data for a single controller."""
        position_dict = data.get("position", {})
        quaternion_dict = data.get("quaternion", {})
        grip_active = data.get("gripActive", False)
        trigger = data.get("trigger", 0)
        button_down = data.get("xButtonDown" if hand == "left" else "aButtonDown", False)

        assert quaternion_dict is not None and all(k in quaternion_dict for k in ["x", "y", "z", "w"]), "Quaternion data missing"
        
        quaternion = np.array([quaternion_dict["x"], quaternion_dict["y"], quaternion_dict["z"], quaternion_dict["w"]])
        position = np.array([position_dict["x"], position_dict["y"], position_dict["z"]])
        transform = pose2transform(position, quaternion)

        controller = self.left_controller if hand == "left" else self.right_controller
        
        # Update controller state with streaming data
        controller.position = position
        controller.quaternion = quaternion
        controller.button_down = button_down

        # Handle trigger for gripper control
        trigger_active = trigger > 0.5
        if trigger_active != controller.trigger_active:
            controller.trigger_active = trigger_active
            logger.info(
                f"(VRControllerInputProvider) 🎯 {hand.upper()} trigger {'PRESSED' if trigger_active else 'RELEASED'} - sending gripper goal"
            )

            # Send gripper control goal - do not specify mode to avoid interfering with position control
            # Reverse behavior: gripper open by default, closes when trigger pressed
            gripper_goal = VRControllerEvent(
                event_type=(TactileVRControllerEventType.TRIGGER_ACTIVE if trigger_active else TactileVRControllerEventType.TRIGGER_RELEASE),
                component_id=hand,
                gripper_closed=not trigger_active,  # Inverted: closed when trigger NOT active
            )
            await self.add_operator_data_to_queue(gripper_goal)
            logger.info(f"(VRControllerInputProvider) ✅ Sent gripper goal for {hand} arm")

            logger.info(
                f"(VRControllerInputProvider) 🤏 {hand.upper()} trigger {'ACTIVE' if trigger_active else 'RELEASED'} - gripper {'OPENED' if trigger_active else 'CLOSED'}"
            )

        # Handle grip button for arm movement control
        if grip_active:
            if not controller.grip_active:
                # Grip just activated - set origin and reset target position
                controller.grip_active = True
                controller.origin_transform = transform.copy()
                logger.info(f"(VRControllerInputProvider) 🔒 {hand.upper()} grip ACTIVATED - sending reset goal")

                # Send reset signal to control loop to reset target position to current robot position
                reset_goal = VRControllerEvent(
                    event_type=TactileVRControllerEventType.GRIP_ACTIVE_INIT,
                    component_id=hand,
                )
                await self.add_operator_data_to_queue(reset_goal)
                logger.info(f"(VRControllerInputProvider) ✅ Sent grip init goal for {hand} arm")

                logger.info(f"(VRControllerInputProvider) 🔒 {hand.upper()} grip activated - arm control enabled")

            # Compute target position
            if controller.origin_transform is not None:
                logger.debug(f"🎯 {hand.upper()} grip active - sending movement goal")

                # Create control goal with relative transform
                goal = VRControllerEvent(
                    event_type=TactileVRControllerEventType.GRIP_ACTIVE,
                    component_id=hand,
                    origin_transform=controller.origin_transform,
                    target_transform=transform,
                )
                await self.add_operator_data_to_queue(goal)
                logger.debug(f"(VRControllerInputProvider) ✅ Sent movement goal for {hand} arm")

    async def _handle_grip_release(self, hand: str):
        """Handle grip release for a controller."""
        if hand == "left":
            controller = self.left_controller
        elif hand == "right":
            controller = self.right_controller
        else:
            return

        if controller.grip_active:
            controller.reset_grip()

            # Send idle goal to stop arm control
            goal = VRControllerEvent(
                event_type=TactileVRControllerEventType.GRIP_RELEASE,
                component_id=hand,
            )
            await self.add_operator_data_to_queue(goal)

            logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} grip released - arm control stopped")

    async def _handle_trigger_release(self, hand: str):
        """Handle trigger release for a controller."""
        controller = self.left_controller if hand == "left" else self.right_controller

        if controller.trigger_active:
            controller.trigger_active = False

            # Send gripper closed goal - reversed behavior: gripper closes when trigger released
            goal = VRControllerEvent(
                event_type=TactileVRControllerEventType.TRIGGER_RELEASE,
                component_id=hand,
                gripper_closed=True,  # Close gripper when trigger released
            )
            await self.add_operator_data_to_queue(goal)

            logger.info(f"(VRControllerInputProvider) 🤏 {hand.upper()} trigger released - gripper CLOSED")

    async def _handle_reset_button_release(self, hand: str):
        """Handle X button release for a controller."""
        goal = VRControllerEvent(
            event_type=TactileVRControllerEventType.RESET_BUTTON_RELEASE,
            component_id=hand,
        )
        await self.add_operator_data_to_queue(goal)

        logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} reset button released - going to initial position")
