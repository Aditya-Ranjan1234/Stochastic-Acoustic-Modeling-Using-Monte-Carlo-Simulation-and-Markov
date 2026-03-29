"""Generate AcoustiX compatible .xml files
"""
import os
import numpy as np
import glob
import open3d as o3d
import argparse


XML_TEMPLATE = '''<scene version="2.1.0">

<!-- Defaults, these can be set via the command line: -Darg=value -->

<!-- Camera and Rendering Parameters -->

    <integrator type="path" id="elm__0" name="elm__0">
        <integer name="max_depth" value="12"/>
    </integrator>

<!-- Emitters -->

    <emitter type="point" id="elm__1" name="elm__1">
        <point name="position" x="4.9397358894348145" y="1.0250400304794312" z="5.932958126068115"/>
        <rgb value="79.577469 79.577469 79.577469" name="intensity"/>
    </emitter>

<!-- Shapes -->

{shapes_materials}

<!-- Volumes -->

</scene>'''


def create_shapes_materials(ply_lists, mat_lists):
    """ Generate shapes and materials for XML files
    """

    shapes_materials = []

    unique_mat_lists = list(set(mat_lists))

    for idx, (ply_file, mat) in enumerate(zip(ply_lists, mat_lists)):
        material_id = f"mat-{mat}"
        shape_id = f"elm__{idx+3}"
        shape_element = f'''
        <shape type="ply" id="{shape_id}" name="{shape_id}">
            <string name="filename" value="{ply_file}"/>
            <boolean name="face_normals" value="true"/>
            <ref id="{material_id}" name="bsdf"/>
        </shape>
        '''
        shapes_materials.append(shape_element)
        
    for idx, unique_mat in enumerate(unique_mat_lists):
        material_id = f"mat-{unique_mat}"
        material_element = f'''
        <bsdf type="twosided" id="{material_id}" name="{material_id}">
            <bsdf type="principled" name="bsdf">
                <rgb value="0.800000 0.800000 0.800000" name="base_color"/>
                <float name="spec_tint" value="0.000000"/>
                <float name="spec_trans" value="0.000000"/>
                <float name="metallic" value="0.000000"/>
                <float name="anisotropic" value="0.000000"/>
                <float name="roughness" value="0.250000"/>
                <float name="sheen" value="0.000000"/>
                <float name="sheen_tint" value="0.500000"/>
                <float name="clearcoat" value="0.000000"/>
                <float name="clearcoat_gloss" value="0.000900"/>
                <float name="specular" value="0.500000"/>
            </bsdf>
        </bsdf>
        '''
        shapes_materials.append(material_element)

    return ''.join(shapes_materials)


def get_mesh_volume_position(mesh):
    """get the mesh volume and center
    """
    bounding_box = mesh.get_axis_aligned_bounding_box()
    
    min_bound = bounding_box.min_bound
    max_bound = bounding_box.max_bound

    mesh_center = (max_bound + min_bound) / 2
    volume = np.prod(max_bound - min_bound)

    return volume, mesh_center


def generate_scene_xml(scene, xyz_min, xyz_max, volume_thres, bounding):
    """ Generate the XML files
    """

    ply_files_path = os.path.join(scene, 'ply_files')
    plt_files = os.path.join(ply_files_path, '*.ply')
    ply_files = glob.glob(plt_files)

    plt_lists = []
    mat_lists = []

    for ply_file in ply_files:
        mesh = o3d.io.read_triangle_mesh(ply_file)
        
        volume, center = get_mesh_volume_position(mesh)

        # drop the object if they are out of the region or volume is small
        if bounding: within_bounds = all(xyz_min[i] <= center[i] <= xyz_max[i] for i in range(3))
        else: within_bounds = True

        if volume < volume_thres or within_bounds == False: # filter the mesh based on the volume
            continue 

        mat_name = "".join(os.path.basename(ply_file).split("_")[:-1])

        plt_lists.append(ply_file)
        mat_lists.append(mat_name)

    # Create shape elements
    shape_material = create_shapes_materials(plt_lists, mat_lists)
    final_xml = XML_TEMPLATE.format(shapes_materials=shape_material)

    # generate XML file
    with open(os.path.join(scene, f"output_scene.xml"), "w") as f:
        f.write(final_xml)
    
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', type=str, default='./scene/demo_scene')
    parser.add_argument('--bounding', action='store_true', default=False, help='scene bounding box')
    parser.add_argument('--volume_thres', type=float, default=0.2)

    args = parser.parse_args()

    xyz_min = [-3.5, -7.5, 1]
    xyz_max = [0, 0, 1.8]

    generate_scene_xml(scene=os.path.abspath(args.scene), xyz_min=xyz_min, xyz_max=xyz_max, volume_thres=args.volume_thres, bounding=args.bounding)
    print("XML file created successfully!")