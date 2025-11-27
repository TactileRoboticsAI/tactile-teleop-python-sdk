import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel

# Import tomllib for Python 3.11+ or tomli for Python 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("For Python < 3.11, please install tomli: pip install tomli")

from tactile_teleop_sdk.base_config import TactileServerConfig
from tactile_teleop_sdk.factory_configs import RawSubscriberConfig, RawPublisherConfig
from tactile_teleop_sdk.camera.camera_config import CameraConfig, from_config as parse_camera_config


class AuthConfig(BaseModel):
    """Authentication configuration for Tactile API."""
    robot_id: str
    api_key: str


@dataclass
class ProtocolConfig:
    """Protocol configuration for teleop communication."""
    protocol: str = "livekit"
    ttl_minutes: int = 120


@dataclass
class DatasetConfig:
    """Dataset configuration for recording."""

    name: str = "tactile_dataset"
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TactileConfig:
    """Complete teleop configuration - declare all the node configurations here.

    Configuration hierarchy (highest to lowest priority):
    1. Runtime arguments passed to __init__ or load()
    2. Environment variables (TACTILE_*)
    3. User config file (tactile.toml)
    4. Default configuration (default.toml)
    """
    auth: AuthConfig
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    server: TactileServerConfig = field(default_factory=TactileServerConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    cameras: List[CameraConfig] = field(default_factory=list)

    # Optional Custom Node Configurations (for advanced users)
    custom_subscribers: List[RawSubscriberConfig] = field(default_factory=list)
    custom_publishers: List[RawPublisherConfig] = field(default_factory=list)

    @classmethod
    def load(
        cls,
        config_file: Optional[str] = None,
        robot_id: Optional[str] = None,
        api_key: Optional[str] = None,
        protocol: Optional[str] = None,
        ttl_minutes: Optional[int] = None,
        backend_url: Optional[str] = None,
        auth_endpoint: Optional[str] = None,
        dataset_name: Optional[str] = None,
        cameras: Optional[List[CameraConfig]] = None,
        **kwargs,
    ) -> "TactileConfig":
        """
        Load configuration with hierarchical priority:
        1. Runtime arguments (highest priority)
        2. Environment variables
        3. Config file (tactile.toml or specified file)
        4. Default configuration (default.toml)

        Args:
            config_file: Path to custom config file (default: "tactile.toml")
            robot_id: Robot identifier (required)
            api_key: API authentication key (required)
            protocol: Communication protocol (default: "livekit")
            ttl_minutes: Token time-to-live in minutes (default: 120)
            backend_url: Backend server URL
            auth_endpoint: Authentication endpoint path
            dataset_name: Name for dataset recording
            cameras: List of camera configurations
            **kwargs: Additional configuration options

        Returns:
            TactileConfig: Fully configured TactileConfig instance

        Raises:
            ValueError: If required configuration (robot_id, api_key) is missing
            FileNotFoundError: If specified config file doesn't exist
        """
        # Step 1: Load default configuration
        config_dict = _load_default_config()

        # Step 2: Load user config file (if exists)
        user_config_path = config_file or "tactile.toml"
        if os.path.exists(user_config_path):
            user_config = _load_toml_file(user_config_path)
            config_dict = _merge_dicts(config_dict, user_config)
        elif config_file is not None:
            # If user explicitly specified a config file, raise error if not found
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Step 3: Override with environment variables
        env_config = _load_from_env()
        config_dict = _merge_dicts(config_dict, env_config)

        # Step 4: Override with runtime arguments (highest priority)
        runtime_config = {}

        if robot_id is not None:
            runtime_config.setdefault("auth", {})["robot_id"] = robot_id
        if api_key is not None:
            runtime_config.setdefault("auth", {})["api_key"] = api_key

        if protocol is not None:
            runtime_config.setdefault("protocol", {})["protocol"] = protocol
        if ttl_minutes is not None:
            runtime_config.setdefault("protocol", {})["ttl_minutes"] = ttl_minutes

        if backend_url is not None:
            runtime_config.setdefault("server", {})["backend_url"] = backend_url
        if auth_endpoint is not None:
            runtime_config.setdefault("server", {})["auth_endpoint"] = auth_endpoint

        if dataset_name is not None:
            runtime_config.setdefault("dataset", {})["name"] = dataset_name

        if cameras is not None:
            runtime_config["cameras"] = cameras

        config_dict = _merge_dicts(config_dict, runtime_config)

        auth_config = config_dict.get("auth", {})
        if not auth_config.get("robot_id") or not auth_config.get("api_key"):
            raise ValueError(
                "Missing required configuration: robot_id and api_key must be provided "
                "via runtime arguments, environment variables (TACTILE_ROBOT_ID, TACTILE_API_KEY), "
                "or config file."
            )

        # Build configuration objects
        return cls._from_dict(config_dict)

    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> "TactileConfig":
        """Internal method to construct TactileConfig from dictionary."""
        # Parse AuthConfig
        auth_data = config_dict.get("auth", {})
        auth = AuthConfig(robot_id=auth_data.get("robot_id", ""), api_key=auth_data.get("api_key", ""))

        # Parse ProtocolConfig
        protocol_data = config_dict.get("protocol", {})
        protocol = ProtocolConfig(
            protocol=protocol_data.get("protocol", "livekit"), ttl_minutes=protocol_data.get("ttl_minutes", 120)
        )

        # Parse ServerConfig
        server_data = config_dict.get("server", {})
        server = TactileServerConfig(
            backend_url=server_data.get("backend_url", "https://10.5.177.78:8443/"),
            auth_endpoint=server_data.get("auth_endpoint", "api/robot/auth-node"),
        )

        # Parse DatasetConfig
        dataset_data = config_dict.get("dataset", {})
        dataset = DatasetConfig(
            name=dataset_data.get("name", "tactile_dataset"), features=dataset_data.get("features", {})
        )

        # Parse CameraConfigs
        cameras_data = config_dict.get("cameras", {})
        if isinstance(cameras_data, list):
            cameras = cameras_data
        elif isinstance(cameras_data, dict):
            cameras = parse_camera_config(cameras_data)
        else:
            cameras = []

        # Parse custom subscribers
        subscribers_list = config_dict.get("custom_subscribers", [])
        custom_subscribers = [RawSubscriberConfig(**sub) if isinstance(sub, dict) else sub for sub in subscribers_list]

        # Parse custom publishers
        publishers_list = config_dict.get("custom_publishers", [])
        custom_publishers = [RawPublisherConfig(**pub) if isinstance(pub, dict) else pub for pub in publishers_list]

        return cls(
            auth=auth,
            protocol=protocol,
            server=server,
            dataset=dataset,
            cameras=cameras,
            custom_subscribers=custom_subscribers,
            custom_publishers=custom_publishers,
        )


def _load_default_config() -> Dict[str, Any]:
    """Load default configuration from bundled default.toml file."""
    default_toml_path = Path(__file__).parent / "default.toml"
    if default_toml_path.exists():
        return _load_toml_file(str(default_toml_path))

    # Fallback to hardcoded defaults if file doesn't exist
    return {
        "protocol": {"protocol": "livekit", "ttl_minutes": 120},
        "server": {"backend_url": "https://10.5.177.78:8443/", "auth_endpoint": "api/robot/auth-node"},
        "dataset": {"name": "tactile_dataset", "features": {}},
        "auth": {"robot_id": "", "api_key": ""},
        "cameras": {},
    }


def _load_toml_file(path: str) -> Dict[str, Any]:
    """Load and parse a TOML configuration file."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables.

    Supported environment variables:
        TACTILE_ROBOT_ID: Robot identifier
        TACTILE_API_KEY: API authentication key
        TACTILE_PROTOCOL: Communication protocol
        TACTILE_TTL_MINUTES: Token time-to-live
        TACTILE_BACKEND_URL: Backend server URL
        TACTILE_AUTH_ENDPOINT: Authentication endpoint
        TACTILE_DATASET_NAME: Dataset name
    """
    config = {}

    # Auth configuration
    robot_id = os.getenv("TACTILE_ROBOT_ID")
    api_key = os.getenv("TACTILE_API_KEY")
    if robot_id or api_key:
        config["auth"] = {}
        if robot_id:
            config["auth"]["robot_id"] = robot_id
        if api_key:
            config["auth"]["api_key"] = api_key

    # Protocol configuration
    protocol = os.getenv("TACTILE_PROTOCOL")
    ttl_minutes = os.getenv("TACTILE_TTL_MINUTES")
    if protocol or ttl_minutes:
        config["protocol"] = {}
        if protocol:
            config["protocol"]["protocol"] = protocol
        if ttl_minutes:
            config["protocol"]["ttl_minutes"] = int(ttl_minutes)

    # Server configuration
    backend_url = os.getenv("TACTILE_BACKEND_URL")
    auth_endpoint = os.getenv("TACTILE_AUTH_ENDPOINT")
    if backend_url or auth_endpoint:
        config["server"] = {}
        if backend_url:
            config["server"]["backend_url"] = backend_url
        if auth_endpoint:
            config["server"]["auth_endpoint"] = auth_endpoint

    # Dataset configuration
    dataset_name = os.getenv("TACTILE_DATASET_NAME")
    if dataset_name:
        config["dataset"] = {"name": dataset_name}

    return config


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Override dictionary (higher priority)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


__all__ = [
    "TactileConfig",
    "AuthConfig",
    "ProtocolConfig",
    "DatasetConfig",
]
