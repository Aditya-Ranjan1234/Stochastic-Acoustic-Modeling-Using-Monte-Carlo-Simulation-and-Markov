import numpy as np
import os
import sys

# Ensure project modules are importable
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from engine.core import MonteCarloSimulation, IrregularScene
from visualization.plots import visualize_ray_paths, plot_impulse_response, generate_heatmap

def main():
    """
    Main entry point for the Stochastic Acoustic Modeling system.
    """
    print("Initializing Stochastic Acoustic Modeling (Monte Carlo + Markov Processes)...")
    
    # 1. Initialize Scene (Irregular geometry)
    # Using mock scene as a baseline for complex geometric interactions
    scene = IrregularScene(geometry_type="irregular")
    
    # 2. Configure Simulation
    num_rays = 1500 # Monte Carlo ray count
    max_bounces = 12 # Markov propagation depth
    materials_path = os.path.join(project_root, "materials", "config.json")
    
    sim = MonteCarloSimulation(
        scene=scene,
        num_rays=num_rays,
        max_bounces=max_bounces,
        materials_path=materials_path
    )
    
    # 3. Define source position in 3D space
    source_pos = [0, 0, 5] # Center of the room at 5m height
    
    # 4. Execute Simulation
    print(f"Executing Monte Carlo simulation with {num_rays} rays...")
    paths, impulse_response = sim.run(source_pos)
    print(f"Simulation complete. Generated {len(paths)} ray paths.")
    
    # 5. Visualization & Output
    print("\nProcessing Analysis Results...")
    results_dir = os.path.join(project_root, "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    print(f"Saving outputs to: {results_dir}")
    
    # Save Ray Paths (3D Visualization)
    ray_plot_path = os.path.join(results_dir, "ray_paths_3d.png")
    visualize_ray_paths(paths, save_path=ray_plot_path)
    print(f" - Ray paths saved to: {ray_plot_path}")
    
    # Save Impulse Response
    ir_plot_path = os.path.join(results_dir, "impulse_response.png")
    plot_impulse_response(impulse_response, save_path=ir_plot_path)
    print(f" - Impulse response saved to: {ir_plot_path}")
    
    # Save Energy Heatmap
    heatmap_path = os.path.join(results_dir, "energy_heatmap.png")
    generate_heatmap(paths, save_path=heatmap_path)
    print(f" - Energy heatmap saved to: {heatmap_path}")
    
    # Save Statistics
    stats_path = os.path.join(results_dir, "simulation_stats.txt")
    total_data_points = len(impulse_response)
    avg_energy = np.mean([er[1] for er in impulse_response]) if impulse_response else 0
    
    with open(stats_path, 'w') as f:
        f.write("Stochastic Acoustic Modeling Simulation Stats\n")
        f.write("============================================\n")
        f.write(f"Monte Carlo Ray Count: {num_rays}\n")
        f.write(f"Markov Bounce Depth: {max_bounces}\n")
        f.write(f"Total Data Points: {total_data_points}\n")
        f.write(f"Average Final Ray Energy: {avg_energy:.4f}\n")
        f.write(f"Simulation Timestamp: {os.path.getmtime(stats_path) if os.path.exists(stats_path) else 'Now'}\n")
    
    print(f" - Statistics report saved to: {stats_path}")
    
    print("\nStochastic Acoustic Modeling System - Research Ready.")
    print("Core Novelty: Markov Chain Transition Matrix integration complete.")

if __name__ == "__main__":
    main()
