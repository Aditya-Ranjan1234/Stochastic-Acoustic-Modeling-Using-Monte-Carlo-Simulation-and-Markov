import os
import sys
import cv2
import numpy as np
import igibson
from igibson.render.mesh_renderer.mesh_renderer_cpu import MeshRenderer
from igibson.render.mesh_renderer.mesh_renderer_settings import MeshRendererSettings
from igibson.render.profiler import Profiler
from igibson.utils.assets_utils import get_scene_path
import json
from scipy.spatial.transform import Rotation as R
import xml.etree.ElementTree as ET
import argparse

OBJECT_PATH = '/media/ztlan/MyDisk/igibson/data/ig_dataset/objects/'

def rpy_to_xyzw(rpy):
    r = R.from_euler('xyz', [rpy[0], rpy[1], rpy[2]])
    return  r.as_quat()


def get_transform_matrix(camera_pose, view_direction, up_vector):
    # Normalize view direction
    view_direction = view_direction / np.linalg.norm(view_direction)

    # Compute right vector (perpendicular to view_direction and up_vector)
    right_vector = np.cross(view_direction, up_vector)
    right_vector = right_vector / np.linalg.norm(right_vector)

    # Recompute the up vector to ensure orthogonality
    up_vector = np.cross(right_vector, view_direction)

    # Create the rotation matrix
    rotation_matrix = np.vstack([right_vector, up_vector, -view_direction]).T  # 3x3 rotation matrix

    # Create the 4x4 transformation matrix
    transform_matrix = np.eye(4)  # Start with an identity matrix
    transform_matrix[:3, :3] = rotation_matrix  # Top-left 3x3 is the rotation matrix
    transform_matrix[:3, 3] = camera_pose       # Last column is the camera position

    return transform_matrix


def load_camera_parameters(file_path):
    camera_parameters = []
    import re

    with open(file_path, 'r') as f:
        for line in f:
            data_match = re.search(r'data: (\S+)', line)
            ir_name = data_match.group(1).replace('.npz', '') if data_match else None

            # Extract and convert to numpy arrays for pos_rx, pos_tx, ori_rx, and ori_tx
            pos_rx_match = re.search(r'pos_rx: \[(.*?)\]', line)
            pos_rx = np.array([float(num) for num in pos_rx_match.group(1).split()])

            pos_tx_match = re.search(r'pos_tx: \[(.*?)\]', line)
            pos_tx = np.array([float(num) for num in pos_tx_match.group(1).split()])

            ori_rx_match = re.search(r'ori_rx: \[(.*?)\]', line)
            ori_rx = np.array([float(num) for num in ori_rx_match.group(1).split()])

            ori_tx_match = re.search(r'ori_tx: \[(.*?)\]', line)
            ori_tx = np.array([float(num) for num in ori_tx_match.group(1).split()])

            # Stack into a list
            parsed_list = [ir_name, pos_rx, pos_tx, ori_rx, ori_tx]
            
            camera_parameters.append(parsed_list)

    return camera_parameters

def save_image(frame, output_dir, ir_name):
    # Save the rendered color and depth images
    rgb_image = frame[0][:,:,:3] # RGB

    # Save the images
    rgb_output_path = os.path.join(output_dir, f"{ir_name}.png")

    cv2.imwrite(rgb_output_path, cv2.cvtColor(rgb_image[:,:,:3] * 255, cv2.COLOR_RGB2BGR))  # Save color image


def json_format(ir_name, parameter, transformation_matrix):
    frame = {
        "file_path":f"{ir_name}.png",
        "w": 256,
        "h": 256,
        "fl_x": parameter[0,0],
        "fl_y": parameter[1,1],
        "cx": parameter[0,2],
        "cy": parameter[1,2],
        "k1": 0,
        "k2": 0,
        "k3": 0,
        "k4": 0,
        "p1": 0,
        "p2": 0,
        "transform_matrix": transformation_matrix.tolist()
    }
    return frame
    

def image_main(scene_folder, scene_name): # interactive scene rendering
    global _mouse_ix, _mouse_iy, down, view_direction

    model_path = os.path.join(igibson.ig_dataset_path, "scenes", f"{scene_name}", "shape", "visual")    

    settings = MeshRendererSettings(msaa=True, enable_shadow=True)
    renderer = MeshRenderer(width=256, height=256, vertical_fov=100, rendering_settings=settings)
    renderer.set_light_position_direction([0, 0, 10], [0, 0, 0])

    i = 0

    # load the environment base frame
    for fn in os.listdir(model_path):
        if fn.endswith("obj"):
            renderer.load_object(os.path.join(model_path, fn))
            renderer.add_instance_group([i])
            i += 1

    # Load the environment base frame object URDF file
    scene_dir = os.path.join(igibson.ig_dataset_path, "scenes", f"{scene_name}")
    objects_urdf_path = os.path.join(scene_dir,f'urdf/{scene_name}_best.urdf')

    tree = ET.parse(objects_urdf_path)
    root = tree.getroot()

    # Iterate over each joint in the URDF
    for joint in root.findall('joint'):
        origin = joint.find('origin')
        if origin is not None:
            # Get rpy and xyz values
            rpy = list(map(float, origin.get('rpy').split()))
            xyz = list(map(float, origin.get('xyz').split()))
            quaternion = rpy_to_xyzw(rpy)

            child_link_name = joint.find('child').get('link')

            link = root.find(f".//link[@name='{child_link_name}']")
            if link is not None:
                category = link.get('category')
                model = link.get('model')
                name = link.get('name')

                bounding_box = link.get('bounding_box')

                if model == 'random':
                    model = np.random.choice(os.listdir(os.path.join(OBJECT_PATH, category)))
                
                if bounding_box is None: continue
                else:
                    bounding_box = list(map(float, bounding_box.split()))

                    model_path = os.path.join(OBJECT_PATH, category, model)        
                    meta_json = os.path.join(model_path, "misc", "metadata.json")

                    with open(meta_json, "r") as f: metadata = json.load(f)
                    ori_bounding_box = np.array(metadata["bbox_size"])

                # Construct the mesh path
                object_path = os.path.join(OBJECT_PATH, category, model, 'shape/visual')

                scale_xyz =  bounding_box / ori_bounding_box

                for fn in os.listdir(object_path):
                    if fn.endswith("obj"):
                        renderer.load_object(os.path.join(object_path, fn), scale=scale_xyz, transform_orn=quaternion, transform_pos=xyz)
                        renderer.add_instance_group([i])
                        i += 1

    print(renderer.visual_objects, renderer.instances)
    print(renderer.material_idx_to_material_instance_mapping, renderer.shape_material_idx)

    # Load camera poses from a predefined txt file
    camera_poses_file = 'camera_pos.txt'  # Change this to your actual file path
    parameters = load_camera_parameters(os.path.join(scene_folder, camera_poses_file))

    # Set up directories to save the images
    output_dir = os.path.join(scene_folder, "images")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    frames_data = []

    # Rendering loop for each camera pose
    for idx, parameter in enumerate(parameters):
        ir_name, pos_rx, _, ori_rx, _ = parameter

        # set the camera position
        camera_pose = np.array(pos_rx)
        view_direction = np.array(ori_rx)
        up_vector = np.array([0,0,1])
        renderer.set_camera(camera_pose, camera_pose + view_direction, up_vector)

        parameter = renderer.get_intrinsics()
        transform_matrix = get_transform_matrix(camera_pose, view_direction, up_vector)

        with Profiler("Render"):
            frame = renderer.render(modes=("rgb"))

        save_image(frame, output_dir, ir_name)
        frame = json_format(ir_name=ir_name, parameter=parameter, transformation_matrix=transform_matrix)

        frames_data.append(frame)

        if idx > 10000:
            break


    data = {"frames": frames_data}
    with open(os.path.join(scene_folder, 'images_transform.json'), 'w') as json_file:
        json.dump(data, json_file, indent=4)

    renderer.release()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_folder', type=str, default='Rs_int')
    parser.add_argument('--scene', type=str, default='Rs_int')
    args = parser.parse_args()

    image_main(args.data_folder, args.scene) # render image