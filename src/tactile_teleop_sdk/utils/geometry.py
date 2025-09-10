import numpy as np


def pose2transform(position: np.ndarray, quaternion: np.ndarray) -> np.ndarray:
    """Convert position and quaternion to a 4x4 homogeneous transformation matrix."""
    x, y, z = position[0], position[1], position[2]
    qx, qy, qz, qw = quaternion[0], quaternion[1], quaternion[2], quaternion[3]

    R = np.array(
        [
            [1 - 2 * (qy**2 + qz**2), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx**2 + qz**2), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx**2 + qy**2)],
        ]
    )

    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = [x, y, z]

    return T


def xyzrpy2transform(x: float, y: float, z: float, roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Convert x, y, z, roll, pitch, yaw to a 4x4 transformation matrix."""
    transformation_matrix = np.eye(4)
    A = np.cos(yaw)
    B = np.sin(yaw)
    C = np.cos(pitch)
    D = np.sin(pitch)
    E = np.cos(roll)
    F = np.sin(roll)
    DE = D * E
    DF = D * F
    transformation_matrix[0, 0] = A * C
    transformation_matrix[0, 1] = A * DF - B * E
    transformation_matrix[0, 2] = B * F + A * DE
    transformation_matrix[0, 3] = x
    transformation_matrix[1, 0] = B * C
    transformation_matrix[1, 1] = A * E + B * DF
    transformation_matrix[1, 2] = B * DE - A * F
    transformation_matrix[1, 3] = y
    transformation_matrix[2, 0] = -D
    transformation_matrix[2, 1] = C * F
    transformation_matrix[2, 2] = C * E
    transformation_matrix[2, 3] = z
    transformation_matrix[3, 0] = 0
    transformation_matrix[3, 1] = 0
    transformation_matrix[3, 2] = 0
    transformation_matrix[3, 3] = 1
    return transformation_matrix


def convert_to_robot_convention(transform_vr: np.ndarray) -> np.ndarray:
    """Convert position and quaternion to robot convention."""

    adj_mat = np.array([[0, 0, -1, 0], [-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]])

    r_adj = xyzrpy2transform(0, 0, 0, -np.pi, 0, -np.pi / 2)
    transform_robot = adj_mat @ transform_vr
    transform_robot = np.dot(transform_robot, r_adj)
    return transform_robot
