import numpy as np


class Pattern:
    def __init__(self, pattern_type="uniform"):
        self.pattern_type = pattern_type

    def heart_pattern(self, facing_angle):
        main_lobe_gain = (1 + np.cos(facing_angle[:, 0]) * np.sin(facing_angle[:, 1])) / 2
        base_level = 0.05
        gain = main_lobe_gain * (1 - base_level) + base_level * 1
        return gain

    def donut_pattern(self, facing_angle):
        main_lobe_gain = np.sin(facing_angle[:, 1])
        base_level = 0.0
        gain = main_lobe_gain * (1 - base_level) + base_level * 1
        return gain

    def uniform_pattern(self, facing_angle):
        gain = np.ones(facing_angle.shape[0])
        return gain

    def get_pattern(self, facing_angle):
        if self.pattern_type == "heart":
            return self.heart_pattern(facing_angle)
        elif self.pattern_type == "donut":
            return self.donut_pattern(facing_angle)
        elif self.pattern_type == "uniform":
            return self.uniform_pattern(facing_angle)
        else:
            raise ValueError(f"Unknown pattern type: {self.pattern_type}")


def unit2angle(unit_ori):
    """transfer unit vector orientation to angle

    Parameters
    ----------
    unit_ori : np.array [n_vector, 3]
        unit orientations in xyz

    Returns
    -------
    angle_ori: np.array [n_vector, 2] in azimuth, elevation
          
    """

    azimuth = np.arctan2(unit_ori[...,1], unit_ori[...,0]) # in 0 ~ 2pi
    elevation = np.pi/2 - np.arctan(unit_ori[...,2] / np.sqrt(unit_ori[...,0]**2 + unit_ori[...,1]**2)) # in 0 ~ pi

    angle_ori = np.stack([azimuth, elevation], axis=-1)
    return angle_ori


def angle_transformation(unit_ori, signal_dir):
    """Orient signal direction based on the 

    Parameters
    ----------
    unit_ori : np.array [x, y, z]
    signal_dir : np.array [n_dirs, 2]

    Returns 
    -------
    oriented_signal_dir: np.array [n_dirs, 2] in azimuth, elevation
    """

    angle_ori = unit2angle(unit_ori) # [n_vector, 2]
    oriented_signal_dir = signal_dir
    oriented_signal_dir[:, 0] -= angle_ori[0]

    return oriented_signal_dir
