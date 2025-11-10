import os
import numpy as np

from glob import glob
from ..config import GRIPPER_OPEN

dir_path = os.path.dirname(os.path.realpath(__file__))


names = [
    os.path.splitext(os.path.basename(f))[0]
    for f in glob(os.path.join(dir_path, '*.npz'))
]

moves = {
    name: np.load(os.path.join(dir_path, f'{name}.npz'))
    for name in names
}


rest_pos = {
    'r_arm.r_shoulder_pitch': 4,
    'r_arm.r_shoulder_roll': -16,
    'r_arm.r_arm_yaw': -12,
    'r_arm.r_elbow_pitch': -18,
    'r_arm.r_forearm_yaw': -26,
    'r_arm.r_wrist_pitch': -57,
    'r_arm.r_wrist_roll': 13,
}

base_pos = {
    'r_arm.r_shoulder_pitch': 4,
    'r_arm.r_shoulder_roll': -16,
    'r_arm.r_arm_yaw': -12,
    'r_arm.r_elbow_pitch': -18,
    'r_arm.r_forearm_yaw': -26,
    'r_arm.r_wrist_pitch': -57,
    'r_arm.r_wrist_roll': 13,
    'r_arm.r_gripper': GRIPPER_OPEN,
}
