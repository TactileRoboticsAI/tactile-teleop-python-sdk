import logging
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum

import numpy as np

from tactile_teleop_sdk.control_providers.base import BaseControlProvider
from tactile_teleop_sdk.config import TeleopConfig
from tactile_teleop_sdk.utils.geometry import pose2transform

logger = logging.getLogger(__name__)


class TactileVRControllerEventType(Enum):
    """Control goal types."""

    IDLE = "idle"  # No button on vr controller pressed
    GRIP_ACTIVE_INIT = "grip_active_init"  # Grip button pressed first time
    GRIP_ACTIVE = "grip_active"  # Grip button held
    GRIP_RELEASE = "grip_release"  # Grip button released
    TRIGGER_ACTIVE = "trigger_active"  # Trigger button pressed
    TRIGGER_RELEASE = "trigger_release"  # Trigger button released
    RESET_BUTTON_RELEASE = "reset_button_release"  # Reset button released

@dataclass
class ArmParallelGripperGoal:
    """Arm goal."""
    arm: str = "right"
    relative_transform: Optional[np.ndarray] = None
    gripper_closed: Optional[bool] = None
    reset_to_init: bool = False
    reset_reference: bool = False

@dataclass
class VRControllerState:
    hand: str = "right"
    grip_active: bool = False
    trigger_active: bool = False
    # 4x4 global transform matrix of the pose where grip was activated
    origin_transform: np.ndarray | None = None
    # 4x4 global transform matrix of the pose where the hand is currently located
    target_transform: np.ndarray | None = None

    def reset_grip(self):
        """Reset grip state but preserve trigger state."""
        self.grip_active = False
        self.origin_transform = None

@dataclass
class VRControllerRobotCommand:
    """Control goal."""
    event_type: TactileVRControllerEventType = TactileVRControllerEventType.IDLE
    arm: str = "right"
    origin_transform: Optional[np.ndarray] = None
    target_transform: Optional[np.ndarray] = None
    gripper_closed: Optional[bool] = None
    

class ParallelGripperVRController(BaseControlProvider):
    """Control provider for VR controllers with parallel grippers.
    
    Processes VR controller data and generates robot control goals.
    Uses composition pattern - transport layer is handled by separate subscriber node.
    """
    
    def __init__(self, config: TeleopConfig, component_ids: List[str] = ["left", "right"]):
        super().__init__(config, component_ids)
        self.left_controller = VRControllerState(hand="left")
        self.right_controller = VRControllerState(hand="right")
        self.left_gripper_closed = True
        self.right_gripper_closed = True
        
    # Implementation of the abstract method of the BaseControlProvider
    def _process_operator_data_queue(self, operator_data_queue: list, component_id: str) -> ArmParallelGripperGoal:
        
        arm_goal = ArmParallelGripperGoal(arm=component_id)
        vr_default_goal = VRControllerRobotCommand(arm=component_id)
        last_grip_active_vr_goal = None
        
        for operator_data in operator_data_queue:
            if operator_data.arm != component_id:
                continue
            if operator_data.event_type == TactileVRControllerEventType.GRIP_ACTIVE_INIT:
                vr_default_goal.origin_transform = operator_data.target_transform
                arm_goal.reset_reference = True
            elif operator_data.event_type == TactileVRControllerEventType.GRIP_ACTIVE:
                last_grip_active_vr_goal = operator_data
            elif operator_data.event_type == TactileVRControllerEventType.GRIP_RELEASE:
                vr_default_goal.target_transform = None
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
                vr_default_goal.origin_transform = None
                vr_default_goal.target_transform = None
                arm_goal.reset_to_init = True
            else:
                raise ValueError(f"Unknown event type: {operator_data.event_type}")

        if last_grip_active_vr_goal is not None:
            vr_reference_transform = last_grip_active_vr_goal.origin_transform  # type: ignore
            vr_target_transform = last_grip_active_vr_goal.target_transform  # type: ignore
            relative_transform = np.linalg.inv(vr_reference_transform) @ vr_target_transform

            # Coordinate transform to global VR frame
            transformation_matrix = np.eye(4)
            transformation_matrix[:3, :3] = vr_reference_transform[:3, :3]

            relative_transform = transformation_matrix @ (relative_transform @ np.linalg.inv(transformation_matrix))

            arm_goal.relative_transform = relative_transform

        arm_goal.gripper_closed = self.left_gripper_closed if component_id == "left" else self.right_gripper_closed
        return arm_goal
    
    async def process_vr_data(self, data: Dict):
        """Process incoming VR controller data.
        
        This method should be registered as callback with subscriber node.
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
        """Process data for a single controller."""
        position = data.get("position", {})
        quaternion = data.get("quaternion", {})  # Get quaternion data directly
        grip_active = data.get("gripActive", False)
        trigger = data.get("trigger", 0)

        assert quaternion is not None and all(k in quaternion for k in ["x", "y", "z", "w"]), "Quaternion data missing"
        quaternion = np.array([quaternion["x"], quaternion["y"], quaternion["z"], quaternion["w"]])
        position = np.array([position["x"], position["y"], position["z"]])
        transform = pose2transform(position, quaternion)

        controller = self.left_controller if hand == "left" else self.right_controller

        # Handle trigger for gripper control
        trigger_active = trigger > 0.5
        if trigger_active != controller.trigger_active:
            controller.trigger_active = trigger_active
            logger.info(
                f"(VRControllerInputProvider) 🎯 {hand.upper()} trigger {'PRESSED' if trigger_active else 'RELEASED'} - sending gripper goal"
            )

            # Send gripper control goal - do not specify mode to avoid interfering with position control
            # Reverse behavior: gripper open by default, closes when trigger pressed
            gripper_goal = VRControllerRobotCommand(
                event_type=(TactileVRControllerEventType.TRIGGER_ACTIVE if trigger_active else TactileVRControllerEventType.TRIGGER_RELEASE),
                arm=hand,
                gripper_closed=not trigger_active,  # Inverted: closed when trigger NOT active
            )
            await self.send_control_goal(gripper_goal)
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
                reset_goal = VRControllerRobotCommand(
                    event_type=TactileVRControllerEventType.GRIP_ACTIVE_INIT,
                    arm=hand,
                )
                await self.send_control_goal(reset_goal)
                logger.info(f"(VRControllerInputProvider) ✅ Sent grip init goal for {hand} arm")

                logger.info(f"(VRControllerInputProvider) 🔒 {hand.upper()} grip activated - arm control enabled")

            # Compute target position
            if controller.origin_transform is not None:
                logger.debug(f"🎯 {hand.upper()} grip active - sending movement goal")

                # Create control goal with relative transform
                goal = VRControllerRobotCommand(
                    event_type=TactileVRControllerEventType.GRIP_ACTIVE,
                    arm=hand,
                    origin_transform=controller.origin_transform,
                    target_transform=transform,
                )
                await self.send_control_goal(goal)
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
            goal = VRControllerRobotCommand(
                event_type=TactileVRControllerEventType.GRIP_RELEASE,
                arm=hand,
            )
            await self.send_control_goal(goal)

            logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} grip released - arm control stopped")

    async def _handle_trigger_release(self, hand: str):
        """Handle trigger release for a controller."""
        controller = self.left_controller if hand == "left" else self.right_controller

        if controller.trigger_active:
            controller.trigger_active = False

            # Send gripper closed goal - reversed behavior: gripper closes when trigger released
            goal = VRControllerRobotCommand(
                event_type=TactileVRControllerEventType.TRIGGER_RELEASE,
                arm=hand,
                gripper_closed=True,  # Close gripper when trigger released
            )
            await self.send_control_goal(goal)

            logger.info(f"(VRControllerInputProvider) 🤏 {hand.upper()} trigger released - gripper CLOSED")

    async def _handle_reset_button_release(self, hand: str):
        """Handle X button release for a controller."""
        goal = VRControllerRobotCommand(
            event_type=TactileVRControllerEventType.RESET_BUTTON_RELEASE,
            arm=hand,
        )
        await self.send_control_goal(goal)

        logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} reset button released - going to initial position")
