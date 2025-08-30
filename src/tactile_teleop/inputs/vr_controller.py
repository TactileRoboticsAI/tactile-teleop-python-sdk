import logging
from dataclasses import dataclass
import asyncio
import os
import json
from tactile_teleop.config import TactileTeleopConfig
from tactile_teleop.inputs.base import BaseInputProvider, ControlGoal, EventType
import numpy as np
from tactile_teleop.utils.livekit_auth import generate_token
from livekit import rtc
from typing import Dict
from tactile_teleop.utils.geometry import pose2transform

logger = logging.getLogger(__name__)
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

@dataclass
class VRControllerState:
    hand: str
    grip_active: bool
    trigger_active: bool
    # 4x4 global transform matrix of the pose where grip was activated 
    origin_transform: np.ndarray
    # 4x4 global transform matrix of the pose where the hand is currently located
    target_transform: np.ndarray

    def reset_grip(self):
        """Reset grip state but preserve trigger state."""
        self.grip_active = False
        self.origin_transform = None


class VRController(BaseInputProvider):
    def __init__(self, config: TactileTeleopConfig):
        self.config = config
        if config.bimanual:
            self.left_controller = VRControllerState(hand="left")
            self.right_controller = VRControllerState(hand="right")
        else:
            self.controller = VRControllerState(hand="right")
        self._data_tasks: set[asyncio.Task] = set()

    async def start(self, room_name: str, participant_identity: str):
        """Start the VR controller."""
        try:
            lk_token = generate_token(room_name=room_name, participant_identity=participant_identity)
        except Exception as e:
            logger.error(f"Failed to generate token: {e}", exc_info=True)
            return

        self.room = rtc.Room()

        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            participant_id = data.participant.identity if data.participant else "unknown"
            topic = getattr(data, 'topic', 'no-topic') if hasattr(data, 'topic') else 'no-topic'

            task = asyncio.create_task(self._handle_data_packet(data))
            
            # Keep track of outstanding packet-processing tasks so we can cancel them on shutdown
            self._data_tasks.add(task)
            task.add_done_callback(self._data_tasks.discard)

        try:
            await self.room.connect(LIVEKIT_URL, lk_token)
            while True:
                await asyncio.sleep(5) # livekit room stay alive signal (less frequent)
        except Exception as e:
            logger.error(f"Failed to connect to LiveKit: {e}")
            return
        finally:
            await self.room.disconnect()


    async def stop(self):
        """Gracefully stop the input provider and cancel outstanding tasks."""
        logger.info("(VRControllerInputProvider) Disconnecting from LiveKit room")

        # Cancel and wait for any in-flight packet processing tasks
        for task in list(self._data_tasks):
            task.cancel()
        if self._data_tasks:
            await asyncio.gather(*self._data_tasks, return_exceptions=True)
        self._data_tasks.clear()

        if hasattr(self, "room") and self.room:
            await self.room.disconnect()
    
    async def _handle_data_packet(self, packet: rtc.DataPacket) -> None:
        """Handle data packet coming from LiveKit."""
        try:
            payload = json.loads(packet.data.decode('utf-8'))
            await self._process_controller_data(payload)
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {packet.data}")
            return
        except Exception as e:
            logger.error(f"Error processing VR data: {e}")
            return

            
    async def _process_controller_data(self, data: Dict):
        """Process incoming VR controller data."""
        left_data = data.get("leftController", {})
        right_data = data.get("rightController", {})
        
        left_active = left_data.get("gripActive", False) or left_data.get("trigger", 0) > 0.5
        right_active = right_data.get("gripActive", False) or right_data.get("trigger", 0) > 0.5
        
        if left_active or right_active:
            logger.info(f"(VRControllerInputProvider) 🎮 Controller ACTIVE - Left: grip={left_data.get('gripActive')}, trigger={left_data.get('trigger'):.1f} | Right: grip={right_data.get('gripActive')}, trigger={right_data.get('trigger'):.1f}")
        else:
            logger.debug(f"(VRControllerInputProvider) 🎮 Controllers idle")

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

        hand = data.get("hand")

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
            logger.info(f"(VRControllerInputProvider) 🎯 {hand.upper()} trigger {'PRESSED' if trigger_active else 'RELEASED'} - sending gripper goal")

            # Send gripper control goal - do not specify mode to avoid interfering with position control
            # Reverse behavior: gripper open by default, closes when trigger pressed
            gripper_goal = ControlGoal(
                event_type=(EventType.TRIGGER_ACTIVE if trigger_active else EventType.TRIGGER_RELEASE),
                arm=hand,
                gripper_closed=not trigger_active,  # Inverted: closed when trigger NOT active
            )
            await self.send_goal(gripper_goal)
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
                reset_goal = ControlGoal(
                    event_type=EventType.GRIP_ACTIVE_INIT,
                    arm=hand,
                )
                await self.send_goal(reset_goal)
                logger.info(f"(VRControllerInputProvider) ✅ Sent grip init goal for {hand} arm")

                logger.info(f"(VRControllerInputProvider) 🔒 {hand.upper()} grip activated - arm control enabled")

            # Compute target position
            if controller.origin_transform is not None:
                logger.debug(f"🎯 {hand.upper()} grip active - sending movement goal")

                # Create control goal with relative transform
                goal = ControlGoal(
                    event_type=EventType.GRIP_ACTIVE,
                    arm=hand,
                    vr_reference_transform=controller.origin_transform,
                    vr_target_transform=transform,
                )
                await self.send_goal(goal)
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
            goal = ControlGoal(
                event_type=EventType.GRIP_RELEASE,
                arm=hand,
            )
            await self.send_goal(goal)

            logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} grip released - arm control stopped")

    async def _handle_trigger_release(self, hand: str):
        """Handle trigger release for a controller."""
        controller = self.left_controller if hand == "left" else self.right_controller

        if controller.trigger_active:
            controller.trigger_active = False

            # Send gripper closed goal - reversed behavior: gripper closes when trigger released
            goal = ControlGoal(
                event_type=EventType.TRIGGER_RELEASE,
                arm=hand,
                gripper_closed=True,  # Close gripper when trigger released
            )
            await self.send_goal(goal)

            logger.info(f"(VRControllerInputProvider) 🤏 {hand.upper()} trigger released - gripper CLOSED")

    async def _handle_reset_button_release(self, hand: str):
        """Handle X button release for a controller."""
        goal = ControlGoal(
            event_type=EventType.RESET_BUTTON_RELEASE,
            arm=hand,
        )
        await self.send_goal(goal)

        logger.info(f"(VRControllerInputProvider) 🔓 {hand.upper()} reset button released - going to initial position")
        
    