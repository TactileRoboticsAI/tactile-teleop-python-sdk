import threading
import time
from typing import Optional

import numpy as np

try:
    import meshcat
    import meshcat.geometry as g
    import meshcat.transformations as tf

    MESHCAT_AVAILABLE = True
except ImportError:
    MESHCAT_AVAILABLE = False
    print("Warning: meshcat not installed. Install with: pip install meshcat")


class TransformVisualizer:
    """Visualize 4x4 transformation matrices as coordinate frames in the browser using meshcat."""

    def __init__(self):
        """
        Initialize the visualizer.
        """
        if not MESHCAT_AVAILABLE:
            raise ImportError("meshcat is required for visualization. Install with: pip install meshcat")

        # Create visualizer without specifying zmq_url to use default
        self.vis = meshcat.Visualizer()

        # Clear any existing objects
        self.vis.delete()

        # self.vis["/Cameras/default"].set_transform(tf.translation_matrix([2, 2, 2]).dot(tf.euler_matrix(0, 0.5, 0.8)))
        # Set up the scene
        # self._setup_scene()

        # Open browser in a separate thread to avoid blocking
        def open_browser_delayed():
            time.sleep(0.5)  # Give server time to start
            try:
                self.vis.open()
            except Exception as e:
                print(f"Could not auto-open browser: {e}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

        print(f"🌐 Meshcat visualizer started at: {self.vis.url()}")

    def _create_coordinate_frame(self, name: str, scale: float = 0.1) -> None:
        """Create a coordinate frame visualization."""
        # X axis (red) - rotate 90 degrees around Z to point along X
        if name == "left_controller":
            y_offset = -scale / 2
        elif name == "right_controller":
            y_offset = scale / 2

        self.vis[f"/{name}/x_axis"].set_object(
            g.Cylinder(height=scale, radius=scale / 20), g.MeshLambertMaterial(color=0xFF0000)
        )
        x_transform = tf.rotation_matrix(np.pi / 2, [0, 0, 1])
        x_transform[0, -1] = scale / 2
        x_transform[1, -1] = y_offset

        self.vis[f"/{name}/x_axis"].set_transform(x_transform)

        # Y axis (green) - rotate 90 degrees around X to point along Y
        self.vis[f"/{name}/y_axis"].set_object(
            g.Cylinder(height=scale, radius=scale / 20), g.MeshLambertMaterial(color=0x00FF00)
        )
        y_transform = np.eye(4)
        y_transform[1, -1] = scale / 2 + y_offset

        self.vis[f"/{name}/y_axis"].set_transform(y_transform)

        # Z axis (blue) - default orientation points up along Z
        self.vis[f"/{name}/z_axis"].set_object(
            g.Cylinder(height=scale, radius=scale / 20), g.MeshLambertMaterial(color=0x0000FF)
        )
        z_transform = tf.rotation_matrix(np.pi / 2, [1, 0, 0])
        z_transform[2, -1] = scale / 2
        z_transform[1, -1] = y_offset
        self.vis[f"/{name}/z_axis"].set_transform(z_transform)

        # Origin sphere
        self.vis[f"/{name}/origin"].set_object(g.Sphere(scale / 10), g.MeshLambertMaterial(color=0xFFFFFF))

        origin_transform = np.eye(4)  # identity matrix
        origin_transform[1, -1] = y_offset

        self.vis[f"/{name}/origin"].set_transform(origin_transform)

    def update_transform(self, name: str, transform: np.ndarray, scale: float = 0.1):
        """
        Update or create a coordinate frame visualization.

        Args:
            name: Name of the coordinate frame
            transform: 4x4 transformation matrix
            scale: Scale of the coordinate frame axes
        """
        if not isinstance(transform, np.ndarray) or transform.shape != (4, 4):
            raise ValueError("Transform must be a 4x4 numpy array")

        # Create the frame if it doesn't exist
        frame_exists = False
        try:
            # Try to check if frame exists by attempting to get its transform
            self.vis[f"/{name}"].get_transform()
            frame_exists = True
        except:
            frame_exists = False

        if not frame_exists:
            self._create_coordinate_frame(name, scale)

        # Update the transform
        self.vis[f"/{name}"].set_transform(transform)

    def update_vr_controllers(
        self,
        left_transform: Optional[np.ndarray] = None,
        right_transform: Optional[np.ndarray] = None,
        scale: float = 0.1,
    ):
        """
        Update VR controller visualizations.

        Args:
            left_transform: 4x4 transform matrix for left controller
            right_transform: 4x4 transform matrix for right controller
            scale: Scale of the coordinate frame axes
        """
        if left_transform is not None:
            self.update_transform("left_controller", left_transform, scale)

        if right_transform is not None:
            self.update_transform("right_controller", right_transform, scale)

    def clear_frame(self, name: str):
        """Remove a coordinate frame from the visualization."""
        self.vis[f"/{name}"].delete()

    def clear_all(self):
        """Clear all visualizations except the grid."""
        self.vis.delete()
        self._setup_scene()

    def close(self):
        """Close the visualizer."""
        # Meshcat doesn't have a direct close method, but we can delete everything
        self.vis.delete()


# Convenience function for quick usage
def create_visualizer() -> Optional[TransformVisualizer]:
    """
    Create a TransformVisualizer instance.

    Returns:
        TransformVisualizer instance or None if meshcat is not available
    """
    try:
        return TransformVisualizer()
    except ImportError:
        print("Warning: Cannot create visualizer. Install meshcat with: pip install meshcat")
        return None
    except Exception as e:
        print(f"Warning: Could not create visualizer: {e}")
        return None
