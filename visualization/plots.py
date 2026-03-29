import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import io
import base64

def get_plot_as_base64():
    """
    Helper to convert current matplotlib figure to base64 string.
    """
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def visualize_ray_paths(paths, save_path=None):
    """
    3D Visualization of ray paths in the irregular scene.
    """
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    for path in paths[:30]: # Visualize a subset of paths
        path = np.array(path)
        ax.plot(path[:, 0], path[:, 1], path[:, 2], alpha=0.6, linewidth=0.8)
    
    ax.set_title("Stochastic Acoustic Ray Tracing (Monte Carlo + Markov)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return None
    else:
        return get_plot_as_base64()

def plot_impulse_response(imp_res, save_path=None):
    """
    Plots the energy vs arrival time (impulse response).
    """
    if not imp_res:
        return ""
        
    times, energies = zip(*imp_res)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(times, energies, s=2, alpha=0.5, color='#4facfe')
    plt.title("Impulse Response (Arrival Time vs Energy)")
    plt.xlabel("Time (s)")
    plt.ylabel("Energy (normalized)")
    plt.grid(True, alpha=0.2, linestyle='--')
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return None
    else:
        return get_plot_as_base64()

def generate_heatmap(paths, save_path=None):
    """
    Generates a simplified energy heatmap on the XY plane.
    """
    all_pos = []
    for path in paths:
        all_pos.extend(path)
    all_pos = np.array(all_pos)
    
    plt.figure(figsize=(10, 8))
    plt.hist2d(all_pos[:, 0], all_pos[:, 1], bins=60, cmap='magma')
    plt.title("Acoustic Energy Heatmap (XY Plane Projection)")
    plt.colorbar(label="Energy density")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return None
    else:
        return get_plot_as_base64()
