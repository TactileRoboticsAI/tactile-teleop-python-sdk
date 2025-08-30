from dataclasses import dataclass
from enum import Enum

class InputType(Enum):
    VR_CONTROLLER = "vr_controller"

@dataclass
class TactileTeleopConfig:
    bimanual: bool = False
    input_type: InputType = InputType.VR_CONTROLLER
