#!/usr/bin/env python3
"""
Test script to verify the hierarchical configuration system.
This script validates that the configuration priority works correctly.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tactile_teleop_sdk.config import TactileConfig


def test_runtime_arguments():
    """Test 1: Runtime arguments have highest priority"""
    print("\n" + "=" * 60)
    print("Test 1: Runtime Arguments (Highest Priority)")
    print("=" * 60)

    try:
        config = TactileConfig.load(robot_id="runtime-robot", api_key="runtime-key", protocol="livekit", ttl_minutes=45)

        assert config.auth.robot_id == "runtime-robot", "Runtime robot_id failed"
        assert config.auth.api_key == "runtime-key", "Runtime api_key failed"
        assert config.protocol.ttl_minutes == 45, "Runtime ttl_minutes failed"

        print("✓ Runtime arguments work correctly")
        return True
    except Exception as e:
        print(f"✗ Runtime arguments failed: {e}")
        return False


def test_environment_variables():
    """Test 2: Environment variables override defaults"""
    print("\n" + "=" * 60)
    print("Test 2: Environment Variables")
    print("=" * 60)

    # Set environment variables
    os.environ["TACTILE_ROBOT_ID"] = "env-robot"
    os.environ["TACTILE_API_KEY"] = "env-key"
    os.environ["TACTILE_TTL_MINUTES"] = "90"

    try:
        config = TactileConfig.load()

        assert config.auth.robot_id == "env-robot", "Env robot_id failed"
        assert config.auth.api_key == "env-key", "Env api_key failed"
        assert config.protocol.ttl_minutes == 90, "Env ttl_minutes failed"

        print("✓ Environment variables work correctly")
        return True
    except Exception as e:
        print(f"✗ Environment variables failed: {e}")
        return False
    finally:
        # Clean up
        del os.environ["TACTILE_ROBOT_ID"]
        del os.environ["TACTILE_API_KEY"]
        del os.environ["TACTILE_TTL_MINUTES"]


def test_config_file():
    """Test 3: Config file loading"""
    print("\n" + "=" * 60)
    print("Test 3: Config File")
    print("=" * 60)

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[auth]
robot_id = "file-robot"
api_key = "file-key"

[protocol]
protocol = "livekit"
ttl_minutes = 60

[dataset]
name = "test_dataset"
"""
        )
        temp_file = f.name

    try:
        config = TactileConfig.load(config_file=temp_file)

        assert config.auth.robot_id == "file-robot", "File robot_id failed"
        assert config.auth.api_key == "file-key", "File api_key failed"
        assert config.protocol.ttl_minutes == 60, "File ttl_minutes failed"
        assert config.dataset.name == "test_dataset", "File dataset name failed"

        print("✓ Config file loading works correctly")
        return True
    except Exception as e:
        print(f"✗ Config file loading failed: {e}")
        return False
    finally:
        os.unlink(temp_file)


def test_hierarchy():
    """Test 4: Configuration hierarchy (runtime > env > file > default)"""
    print("\n" + "=" * 60)
    print("Test 4: Configuration Hierarchy")
    print("=" * 60)

    # Create config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[auth]
robot_id = "file-robot"
api_key = "file-key"

[protocol]
ttl_minutes = 60
"""
        )
        temp_file = f.name

    # Set environment variable
    os.environ["TACTILE_TTL_MINUTES"] = "90"

    try:
        # Runtime should override env which overrides file
        config = TactileConfig.load(config_file=temp_file, ttl_minutes=45)  # Runtime override

        assert config.auth.robot_id == "file-robot", "File robot_id not loaded"
        assert config.auth.api_key == "file-key", "File api_key not loaded"
        assert config.protocol.ttl_minutes == 45, "Runtime didn't override env/file"

        print("✓ Hierarchy: runtime > env > file > default works correctly")

        # Test without runtime arg (env should override file)
        config2 = TactileConfig.load(config_file=temp_file)
        assert config2.protocol.ttl_minutes == 90, "Env didn't override file"

        print("✓ Hierarchy: env > file works correctly")
        return True
    except Exception as e:
        print(f"✗ Hierarchy test failed: {e}")
        return False
    finally:
        os.unlink(temp_file)
        if "TACTILE_TTL_MINUTES" in os.environ:
            del os.environ["TACTILE_TTL_MINUTES"]


def test_required_fields():
    """Test 5: Required field validation"""
    print("\n" + "=" * 60)
    print("Test 5: Required Field Validation")
    print("=" * 60)

    try:
        # This should fail because robot_id and api_key are required
        config = TactileConfig.load()
        print("✗ Should have raised ValueError for missing required fields")
        return False
    except ValueError as e:
        if "robot_id and api_key must be provided" in str(e):
            print(f"✓ Required field validation works: {e}")
            return True
        else:
            print(f"✗ Wrong error message: {e}")
            return False


def test_default_config():
    """Test 6: Default configuration loading"""
    print("\n" + "=" * 60)
    print("Test 6: Default Configuration")
    print("=" * 60)

    try:
        config = TactileConfig.load(robot_id="test-robot", api_key="test-key")

        # Check default values
        assert config.protocol.protocol == "livekit", "Default protocol wrong"
        assert config.protocol.ttl_minutes == 120, "Default ttl_minutes wrong"
        assert config.server.backend_url == "https://10.5.177.78:8443/", "Default backend_url wrong"

        print("✓ Default configuration loads correctly")
        return True
    except Exception as e:
        print(f"✗ Default configuration failed: {e}")
        return False


def test_camera_config():
    """Test 7: Camera configuration from file"""
    print("\n" + "=" * 60)
    print("Test 7: Camera Configuration")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[auth]
robot_id = "camera-robot"
api_key = "camera-key"

[cameras.front]
name = "Front Camera"
type = "monocular"
mode = "streaming"
fps = 30
frame_width = 640
frame_height = 480
cam_index = 0
capture_api = 200

[cameras.wrist]
name = "Wrist Camera"
type = "stereo"
mode = "hybrid"
fps = 60
frame_width = 1280
frame_height = 720
cam_index = 2
capture_api = 200
"""
        )
        temp_file = f.name

    try:
        config = TactileConfig.load(config_file=temp_file)

        assert len(config.cameras) == 2, f"Expected 2 cameras, got {len(config.cameras)}"

        # Check front camera (cameras are parsed from dict, order may vary)
        camera_names = [cam.name for cam in config.cameras]
        assert "front" in camera_names or "Front Camera" in [
            cam.name for cam in config.cameras
        ], "Front camera not found"

        print(f"✓ Camera configuration works: {len(config.cameras)} cameras loaded")
        for cam in config.cameras:
            print(f"  - {cam.name}: {cam.type}, {cam.frame_width}x{cam.frame_height}@{cam.fps}fps")
        return True
    except Exception as e:
        print(f"✗ Camera configuration failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_file)


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Tactile Teleop SDK - Configuration System Tests")
    print("=" * 60)

    tests = [
        test_runtime_arguments,
        test_environment_variables,
        test_config_file,
        test_hierarchy,
        test_required_fields,
        test_default_config,
        test_camera_config,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
