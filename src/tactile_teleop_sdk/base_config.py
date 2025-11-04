"""
Base configuration infrasturcture for node management.
Advanced users can extend these for custom node types.
"""

from dataclasses import dataclass

@dataclass
class TactileServerConfig:
    backend_url: str = "https://localhost:8443/" #"https://teleop.tactilerobotics.ai"
    auth_endpoint: str = "api/robot/auth-node"


