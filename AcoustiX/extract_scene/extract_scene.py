import os
import xml.etree.ElementTree as ET
import numpy as np
import open3d as o3d
import trimesh
import json

# Function to parse rpy (roll, pitch, yaw) to a rotation matrix
def rpy_to_rotation_matrix(roll, pitch, yaw):
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(roll), -np.sin(roll)],
                    [0, np.sin(roll), np.cos(roll)]])
    
    R_y = np.array([[np.cos(pitch), 0, np.sin(pitch)],
                    [0, 1, 0],
                    [-np.sin(pitch), 0, np.cos(pitch)]])
    
    R_z = np.array([[np.cos(yaw), -np.sin(yaw), 0],
                    [np.sin(yaw), np.cos(yaw), 0],
                    [0, 0, 1]])
    
    R = np.dot(R_z, np.dot(R_y, np.dot(R_x, np.eye(3))))
    return R

# Function to load and transform a mesh
def load_and_transform_mesh(mesh_path, translation, rotation_matrix, bounding_box, ori_bounding_box):
    # Load the mesh
    mesh = o3d.io.read_triangle_mesh(mesh_path)

    # Convert the vertices of the mesh to a numpy array
    vertices = np.asarray(mesh.vertices)

    # Scale the vertices
    scaled_vertices = vertices * bounding_box / ori_bounding_box
    mesh.vertices = o3d.utility.Vector3dVector(scaled_vertices)

    mesh.rotate(rotation_matrix, center=(0, 0, 0))    
    mesh.translate(translation)
    
    return mesh

def simplify_mesh(mesh, target_reduction=0.25):
    """
    Simplify the mesh using quadric decimation.
    target_reduction is the fraction of triangles to retain.
    """
    target_triangle_count = int(len(mesh.triangles) * target_reduction)
    simplified_mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangle_count)
    return simplified_mesh


# scene dir
scene_base_dir = '/media/ztlan/MyDisk/igibson/data/ig_dataset/scenes'
scene_name = 'Pomaria_2_int'

scene_dir = os.path.join(scene_base_dir, scene_name)
urdf_file_path = os.path.join(scene_dir,f'urdf/{scene_name}_best.urdf')

# save mesh ply files
mesh_collection = os.path.join(f'{scene_name}', 'ply_files')
os.makedirs(mesh_collection, exist_ok=True)

# here, get the INRAS scene boundary and DiffRIR mesh representations
room_mesh_path = os.path.join(f'{scene_name}', 'room_mesh')
os.makedirs(room_mesh_path, exist_ok=True)

# base scene structure
base_scene = os.path.join(scene_dir, "shape/collision")
scene_elements = os.listdir(base_scene)
for scene_element in scene_elements:
    mesh = o3d.io.read_triangle_mesh(os.path.join(base_scene, scene_element))
    # mesh = simplify_mesh(mesh, target_reduction=0.5)
    # Save the mesh as a .ply file
    ply_file_path = os.path.join(mesh_collection, scene_element[:-4] + ".ply")
    o3d.io.write_triangle_mesh(ply_file_path, mesh)

    #  save inras mesh
    room_mesh_file_path = os.path.join(room_mesh_path, scene_element[:-4] + ".ply")
    o3d.io.write_triangle_mesh(room_mesh_file_path, mesh)


# Load the URDF file
tree = ET.parse(urdf_file_path)
root = tree.getroot()

# Base path for object files
object_path = '/media/ztlan/MyDisk/igibson/data/ig_dataset/objects/'

# Iterate over each joint in the URDF
for joint in root.findall('joint'):
    origin = joint.find('origin')
    if origin is not None:
        # Get rpy and xyz values
        rpy = list(map(float, origin.get('rpy').split()))
        xyz = list(map(float, origin.get('xyz').split()))
        
        rotation_matrix = rpy_to_rotation_matrix(rpy[0], rpy[1], rpy[2])

        # Find the child link name
        child_link_name = joint.find('child').get('link')
        
        # Find the corresponding link to get its category and model
        link = root.find(f".//link[@name='{child_link_name}']")
        if link is not None:
            category = link.get('category')
            model = link.get('model')
            name = link.get('name')

            bounding_box = link.get('bounding_box')

            if model == 'random':
                model = np.random.choice(os.listdir(os.path.join(object_path, category)))
            
            if bounding_box is None:
                continue
            else:
                bounding_box = list(map(float, bounding_box.split()))

                model_path = os.path.join(object_path, category, model)        
                meta_json = os.path.join(model_path, "misc", "metadata.json")

                with open(meta_json, "r") as f:
                    metadata = json.load(f)

                ori_bounding_box = np.array(metadata["bbox_size"])

            # Construct the mesh path
            mesh_path = os.path.join(object_path, category, model, 'shape/collision', f'{model}_cm.obj')
            
            
            # Load and transform the mesh
            if os.path.exists(mesh_path): # a single mesh data
                combined_mesh = o3d.geometry.TriangleMesh()
                mesh = load_and_transform_mesh(mesh_path, xyz, rotation_matrix, bounding_box, ori_bounding_box)
                combined_mesh += mesh
                # o3d.io.write_triangle_mesh(os.path.join(mesh_collection, f"{category}_{model}_{name}.ply"), combined_mesh)
                combined_mesh = simplify_mesh(combined_mesh)
                o3d.io.write_triangle_mesh(os.path.join(mesh_collection, f"{name}.ply"), combined_mesh)

            else: # joint mesh data points
                try:
                    combined_mesh = o3d.geometry.TriangleMesh()
                    files = os.listdir(os.path.join(object_path, category, model, 'shape/collision'))
                    for file in files:
                        mesh_path = os.path.join(object_path, category, model, 'shape/collision', file)
                        mesh = load_and_transform_mesh(mesh_path, xyz, rotation_matrix, bounding_box, ori_bounding_box)
                        combined_mesh += mesh

                    combined_mesh = simplify_mesh(combined_mesh)
                    o3d.io.write_triangle_mesh(os.path.join(mesh_collection, f"{name}.ply"), combined_mesh)
                except:
                    print(f"Mesh file not found: {mesh_path}")

