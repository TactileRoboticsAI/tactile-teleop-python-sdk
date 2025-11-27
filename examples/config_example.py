"""
Example demonstrating the hierarchical configuration system for Tactile Teleop SDK.

Configuration Priority (highest to lowest):
1. Runtime arguments
2. Environment variables (TACTILE_*)
3. Config file (tactile.toml)
4. Default configuration
"""

from tactile_teleop_sdk.config import TactileConfig
from tactile_teleop_sdk.camera.camera_config import CameraConfig, CameraType, CameraMode


def example_1_runtime_args():
    """Example 1: Configuration via runtime arguments (highest priority)"""
    print("=" * 60)
    print("Example 1: Configuration via Runtime Arguments")
    print("=" * 60)
    
    config = TactileConfig.load(
        robot_id="my-robot-123",
        api_key="my-secret-api-key",
        protocol="livekit",
        ttl_minutes=60,
        dataset_name="my_custom_dataset"
    )
    
    print(f"Robot ID: {config.auth.robot_id}")
    print(f"API Key: {config.auth.api_key[:10]}...")
    print(f"Protocol: {config.protocol.protocol}")
    print(f"TTL: {config.protocol.ttl_minutes} minutes")
    print(f"Dataset: {config.dataset.name}")
    print()


def example_2_env_variables():
    """Example 2: Configuration via environment variables
    
    Before running this, set environment variables:
        export TACTILE_ROBOT_ID="my-robot-456"
        export TACTILE_API_KEY="my-env-api-key"
        export TACTILE_PROTOCOL="livekit"
        export TACTILE_TTL_MINUTES="90"
    """
    print("=" * 60)
    print("Example 2: Configuration via Environment Variables")
    print("=" * 60)
    
    try:
        config = TactileConfig.load()
        print(f"Robot ID: {config.auth.robot_id}")
        print(f"API Key: {config.auth.api_key[:10]}...")
        print(f"Protocol: {config.protocol.protocol}")
        print(f"TTL: {config.protocol.ttl_minutes} minutes")
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure to set TACTILE_ROBOT_ID and TACTILE_API_KEY environment variables")
    print()


def example_3_config_file():
    """Example 3: Configuration via tactile.toml file
    
    Create a tactile.toml file in your current directory:
    
    [auth]
    robot_id = "my-robot-789"
    api_key = "my-file-api-key"
    
    [protocol]
    protocol = "livekit"
    ttl_minutes = 120
    
    [cameras.front]
    name = "Front Camera"
    type = "monocular"
    fps = 30
    """
    print("=" * 60)
    print("Example 3: Configuration via Config File")
    print("=" * 60)
    
    try:
        # Will look for tactile.toml in current directory
        config = TactileConfig.load()
        print(f"Robot ID: {config.auth.robot_id}")
        print(f"API Key: {config.auth.api_key[:10]}...")
        print(f"Number of cameras: {len(config.cameras)}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Create a tactile.toml file with auth credentials")
    print()


def example_4_custom_config_file():
    """Example 4: Configuration from custom config file"""
    print("=" * 60)
    print("Example 4: Configuration from Custom Config File")
    print("=" * 60)
    
    try:
        config = TactileConfig.load(config_file="my_custom_config.toml")
        print(f"Loaded from custom file: my_custom_config.toml")
        print(f"Robot ID: {config.auth.robot_id}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Create my_custom_config.toml with your configuration")
    except ValueError as e:
        print(f"Error: {e}")
    print()


def example_5_mixed_hierarchy():
    """Example 5: Mixed configuration with hierarchy
    
    Demonstrates priority system where runtime args override everything
    """
    print("=" * 60)
    print("Example 5: Mixed Configuration Hierarchy")
    print("=" * 60)
    
    # Even if tactile.toml exists with different values,
    # runtime arguments take precedence
    config = TactileConfig.load(
        robot_id="override-robot-id",  # This overrides any other source
        api_key="override-api-key",     # This overrides any other source
        ttl_minutes=45                   # This overrides any other source
    )
    
    print(f"Robot ID (from runtime): {config.auth.robot_id}")
    print(f"API Key (from runtime): {config.auth.api_key[:10]}...")
    print(f"TTL (from runtime): {config.protocol.ttl_minutes} minutes")
    print(f"Protocol (from file/env/default): {config.protocol.protocol}")
    print()


def example_6_with_cameras():
    """Example 6: Configuration with camera setup"""
    print("=" * 60)
    print("Example 6: Configuration with Cameras")
    print("=" * 60)
    
    # Define cameras programmatically
    front_camera = CameraConfig(
        name="Front Camera",
        type=CameraType.MONOCULAR,
        mode=CameraMode.STREAMING,
        fps=30,
        frame_width=640,
        frame_height=480,
        cam_index=0
    )
    
    wrist_camera = CameraConfig(
        name="Wrist Camera",
        type=CameraType.MONOCULAR,
        mode=CameraMode.HYBRID,
        fps=30,
        frame_width=640,
        frame_height=480,
        cam_index=2
    )
    
    config = TactileConfig.load(
        robot_id="camera-robot",
        api_key="camera-api-key",
        cameras=[front_camera, wrist_camera]
    )
    
    print(f"Number of cameras: {len(config.cameras)}")
    for cam in config.cameras:
        print(f"  - {cam.name}: {cam.type}, {cam.frame_width}x{cam.frame_height} @ {cam.fps}fps")
    print()


def example_7_validation():
    """Example 7: Configuration validation (missing required fields)"""
    print("=" * 60)
    print("Example 7: Configuration Validation")
    print("=" * 60)
    
    try:
        # This will fail because robot_id and api_key are required
        config = TactileConfig.load(
            protocol="livekit",
            ttl_minutes=60
        )
    except ValueError as e:
        print(f"✓ Validation works! Error: {e}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Tactile Teleop SDK - Configuration Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    example_1_runtime_args()
    example_2_env_variables()
    example_3_config_file()
    example_4_custom_config_file()
    example_5_mixed_hierarchy()
    example_6_with_cameras()
    example_7_validation()
    
    print("=" * 60)
    print("Configuration Priority Summary:")
    print("=" * 60)
    print("1. Runtime arguments (highest priority)")
    print("2. Environment variables (TACTILE_*)")
    print("3. Config file (tactile.toml)")
    print("4. Default configuration (lowest priority)")
    print("=" * 60)

