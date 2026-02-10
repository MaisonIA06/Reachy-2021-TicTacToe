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
    'r_arm.r_shoulder_pitch': 6,
    'r_arm.r_shoulder_roll': -7,
    'r_arm.r_arm_yaw': -25,
    'r_arm.r_elbow_pitch': -84,
    'r_arm.r_forearm_yaw': -10,
    'r_arm.r_wrist_pitch': -9,
    'r_arm.r_wrist_roll': 47,
}

base_pos = {
    'r_arm.r_shoulder_pitch': 6,
    'r_arm.r_shoulder_roll': -7,
    'r_arm.r_arm_yaw': -25,
    'r_arm.r_elbow_pitch': -84,
    'r_arm.r_forearm_yaw': -10,
    'r_arm.r_wrist_pitch': -9,
    'r_arm.r_wrist_roll': 47,
    'r_arm.r_gripper': GRIPPER_OPEN,
}
