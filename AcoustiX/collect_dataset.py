import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tensorflow as tf
gpu_num = 0 # Use "" to use the CPU
os.environ["CUDA_VISIBLE_DEVICES"] = f"{gpu_num}"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
gpus = tf.config.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(gpus[0], True)
tf.get_logger().setLevel('ERROR')
tf.random.set_seed(1) # Set global random seed for reproducibility

import json
import numpy as np
from tqdm import tqdm
import yaml
from simu_utils import ir_simulation, plot_figure, save_ir, load_cfg, generate_rx_samples
from shutil import copyfile
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Help for simulation files.")
    parser.add_argument('--save-data', action="store_true", help='save the simulated impulse response data')

    parser.add_argument('--config-file', default="./simu_config/basic_config.yml", help='config file for the impulse response rendering')
    parser.add_argument('--num-samples', default=1000, help='num of simulated impulse response')
    parser.add_argument('--num-batch', default=20, help='num of IR per batch to be simulated')
    
    parser.add_argument('--scene-file', default='./scene/example_scene/example_scene.xml', help='path to the scene XML file')
    parser.add_argument('--dataset-name', default='test', help='dataset name')
    

    args = parser.parse_args()

    save_data = args.save_data
    show_image = not save_data
    config_file = args.config_file

    # output path setup
    dataset_name = args.dataset_name
    scene_path = args.scene_file
    scene_folder = os.path.dirname(os.path.abspath(scene_path))
    output_path = os.path.join(scene_folder, dataset_name)

    # back up the simulation config
    os.makedirs(output_path, exist_ok=True) 
    copyfile(config_file,  os.path.join(output_path, "config.yml"))

    ## simulation setup
    simu_config = load_cfg(config_file=config_file)

    # scene boundary setup
    xyz_min = [-3,-3,-1]
    xyz_max = [3,3,1]

    # simulation number
    n_random_samples = args.num_batch # each simulation batch simulation these random samples
    num_sample = args.num_samples # total simulation samples
    num_iter = int(num_sample / n_random_samples)

    # this example shows the fixed tx positions
    tx_poses = [[1.0, -2.3, 0]]
    tx_oris = [[-0.9, -1.2, 0]]

    data = {"speaker": {"positions": tx_poses, "orientations": tx_oris}}
    with open(os.path.join(output_path, 'speaker_data.json'), 'w') as json_file:
        json.dump(data, json_file, indent=4)

    for tx_ind, (tx_pos, tx_ori) in enumerate(zip(tx_poses, tx_oris)):
        tx_pos = np.array(tx_pos)
        tx_ori = np.array(tx_ori)
        tx_ori /= np.linalg.norm(tx_ori)

        pbar = tqdm(range(0, num_iter))
        for iter in pbar:
            prefix = (tx_ind+1) * n_random_samples * iter
            pbar.set_description(f"tx pos: {str(tx_pos)}")
            
            # randomly generate samples
            rx_pos, rx_ori = generate_rx_samples(n_random_samples=n_random_samples, xyz_max=xyz_max, xyz_min=xyz_min)

            # ir simulations
            ir_time_all, rx_pos, rx_ori = ir_simulation(scene_path=scene_path, rx_pos=rx_pos, tx_pos=tx_pos, rx_ori=rx_ori, tx_ori=tx_ori, simu_config=simu_config)

            # save or show the ir samples
            if show_image == True:
                plot_figure(ir_samples=ir_time_all, rx_pos=rx_pos, tx_pos=tx_pos, rx_ori=rx_ori, tx_ori=tx_ori, fs=simu_config['fs'])

            if save_data == True:                
                save_ir(ir_samples=ir_time_all, rx_pos=rx_pos, rx_ori=rx_ori, tx_pos=tx_pos, tx_ori=tx_ori, save_path=output_path, prefix=prefix)