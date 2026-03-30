from flask import Flask, jsonify, request, send_from_directory
import os
import sys
import numpy as np
import json

# Ensure project modules are importable (for Vercel api/ subfolder)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from engine.core import MonteCarloSimulation, create_irregular_room
from visualization.plots import visualize_ray_paths, plot_impulse_response, generate_heatmap
from scipy.stats import beta
import matplotlib
matplotlib.use('Agg')

from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# --- Local Static File Serving ---
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'public')

@app.route('/')
def index():
    return send_from_directory(PUBLIC_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(PUBLIC_DIR, path)

# --- Helper Functions for New Tabs ---

def calculate_canyon_matrix(h_w, alpha_f, alpha_g, mu):
    """
    Calculates 5x5 transition matrix for Street Canyon:
    0: Left Facade, 1: Right Facade, 2: Ground, 3: Sky, 4: Receiver
    """
    # View factors
    f_ff = h_w / (h_w + 1)
    f_fg = 1 / (2 * (h_w + 1))
    f_fs = 1 / (2 * (h_w + 1))
    
    # Distance approximation (simplified for demo)
    d = 10.0 # meter
    att = np.exp(-mu * d)
    
    # Matrix P[i][j]
    P = np.zeros((5, 5))
    
    # From Facades (0, 1)
    # To other facade
    P[0, 1] = f_ff * (1 - alpha_f) * att
    P[1, 0] = f_ff * (1 - alpha_f) * att
    # To ground
    P[0, 2] = f_fg * (1 - alpha_g) * att
    P[1, 2] = f_fg * (1 - alpha_g) * att
    # To sky (absorption/loss)
    P[0, 3] = f_fs
    P[1, 3] = f_fs
    # To receiver (small probability)
    P[0, 4] = 0.05 * (1 - alpha_f)
    P[1, 4] = 0.05 * (1 - alpha_f)
    
    # From Ground (2)
    P[2, 0] = 0.4 * (1 - alpha_f) * att
    P[2, 1] = 0.4 * (1 - alpha_f) * att
    P[2, 3] = 0.2 # Sky
    
    # Sky (3) - energy escapes, but for stationary demo we re-inject to source
    P[3, 0] = 0.4
    P[3, 1] = 0.4
    P[3, 2] = 0.2
    
    # Receiver (4) - transitions back to ground/facades (simplified)
    P[4, 0] = 0.3
    P[4, 1] = 0.3
    P[4, 2] = 0.4
    
    # Normalize rows
    for i in range(5):
        row_sum = np.sum(P[i])
        if row_sum > 0:
            P[i] = P[i] / row_sum
            
    return P

def solve_stationary(P):
    # Solve pi * P = pi => pi * (P - I) = 0
    # Add constraint sum(pi) = 1
    n = P.shape[0]
    A = np.transpose(P) - np.eye(n)
    A[-1] = np.ones(n)
    b = np.zeros(n)
    b[-1] = 1
    try:
        pi = np.linalg.solve(A, b)
        return np.maximum(pi, 0) # Ensure non-negative
    except:
        return np.ones(n) / n

@app.route('/api/canyon', methods=['POST'])
@app.route('/canyon', methods=['POST'])
def canyon_sim():
    data = request.json
    h_w = float(data.get('h_w', 1.0))
    alpha_f = float(data.get('alpha_f', 0.3))
    alpha_g = float(data.get('alpha_g', 0.2))
    mu = float(data.get('mu', 0.01))
    lw = float(data.get('lw', 90))
    
    P = calculate_canyon_matrix(h_w, alpha_f, alpha_g, mu)
    pi = solve_stationary(P)
    
    # SPL Calculation
    r = 5.0 # distance to receiver
    pi_receiver = pi[4]
    spl = lw + 10 * np.log10(max(pi_receiver, 1e-10)) - 20 * np.log10(r)
    
    return jsonify({
        "matrix": P.tolist(),
        "distribution": pi.tolist(),
        "spl": round(float(spl), 2)
    })

@app.route('/api/convergence', methods=['POST'])
def convergence_sim():
    # Pre-calculated "true" mean for demo
    true_mean = 68.5
    
    samples = []
    running_means = []
    ci_widths = []
    
    # Generate stochastic samples
    n_points = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    all_spls = []
    
    for n in range(1, 10001):
        # Sample stochastic parameters
        s_lw = np.random.normal(95, 3)
        s_alpha = np.random.beta(2, 5)
        # Simplified SPL result for convergence demo
        s_spl = s_lw - 20 - (s_alpha * 15) + np.random.normal(0, 1)
        all_spls.append(s_spl)
        
        if n in n_points:
            mu_n = np.mean(all_spls)
            sigma_n = np.std(all_spls) if len(all_spls) > 1 else 3.0
            ci = 1.96 * sigma_n / np.sqrt(n)
            
            samples.append(n)
            running_means.append(float(mu_n))
            ci_widths.append(float(ci))
            
    return jsonify({
        "n": samples,
        "means": running_means,
        "ci": ci_widths,
        "true_mean": true_mean
    })

@app.route('/api/grid', methods=['POST'])
@app.route('/grid', methods=['POST'])
def grid_sim():
    data = request.json
    profile = data.get('profile', 'Mixed')
    
    grid_spl = np.zeros((4, 4))
    grid_ci = np.zeros((4, 4))
    
    for i in range(4):
        for j in range(4):
            if profile == 'Dense Urban':
                h_w = np.random.uniform(2.0, 3.0)
                alpha = np.random.beta(1, 4) # low absorption
                noise_std = np.random.uniform(0.8, 1.8) # Randomized low uncertainty
            elif profile == 'Suburban':
                h_w = np.random.uniform(0.5, 1.2)
                alpha = np.random.beta(4, 2) # high absorption
                noise_std = np.random.uniform(1.8, 3.5) # Randomized medium uncertainty
            else: # Mixed
                h_w = np.random.uniform(0.5, 2.5)
                alpha = np.random.beta(2, 5)
                noise_std = np.random.uniform(3.0, 6.0) # Randomized high uncertainty
                
            # Simulate M=500 trials per cell (simplified for performance)
            base_lw = 95 + np.random.normal(0, 1.5) # Add cell-specific source variation
            cell_spls = base_lw - 10/h_w - (alpha * 20) + np.random.normal(0, noise_std, 500)
            
            grid_spl[i, j] = np.mean(cell_spls)
            grid_ci[i, j] = 1.96 * np.std(cell_spls) / np.sqrt(500)
            
    return jsonify({
        "spl_grid": grid_spl.tolist(),
        "ci_grid": grid_ci.tolist()
    })

# --- CITY PLANNER ENDPOINTS ---

@app.route('/api/planner/simulate', methods=['POST'])
@app.route('/planner/simulate', methods=['POST'])
def planner_sim():
    """
    Handles interactive city builder simulation.
    Input: list of buildings (x, y, h, material) and sources.
    Output: 10x10 high-res heatmap and variance map.
    """
    data = request.json
    buildings = data.get('buildings', [])
    sources = data.get('sources', [])
    
    grid_size = 10
    spl_map = np.zeros((grid_size, grid_size))
    var_map = np.zeros((grid_size, grid_size))
    
    materials = {
        "glass": {"alpha": 0.05, "noise": 0.8},
        "concrete": {"alpha": 0.2, "noise": 1.5},
        "vegetation": {"alpha": 0.7, "noise": 3.5},
        "barrier": {"alpha": 0.9, "noise": 0.5}
    }
    
    for i in range(grid_size):
        for j in range(grid_size):
            # 1. Calculate source-to-receiver noise with building attenuation
            base_noise_energy = 0
            for src in sources:
                dist = np.sqrt((src['x'] - i)**2 + (src['y'] - j)**2)
                
                # Check if any building is between source and current cell
                attenuation = 1.0
                for b in buildings:
                    # Simple shadowing: if building is on the same line or very close
                    # For a 10x10 grid, we check if the building is roughly between
                    if min(src['x'], i) <= b['x'] <= max(src['x'], i) and \
                       min(src['y'], j) <= b['y'] <= max(src['y'], j):
                        if (b['x'] != i or b['y'] != j) and (b['x'] != src['x'] or b['y'] != src['y']):
                            attenuation *= (1.0 - materials.get(b['material'], materials['concrete'])['alpha'])
                
                # Inverse square law with shadowing
                base_noise_energy += (src['intensity'] * attenuation) / (dist**2 + 1.0)
            
            # 2. Local surface interactions
            local_alpha = 0.1
            local_h_w = 0.5
            local_noise_std = 1.0
            
            for b in buildings:
                if b['x'] == i and b['y'] == j:
                    m = materials.get(b['material'], materials['concrete'])
                    local_alpha = m['alpha']
                    local_h_w = b['h'] / 5.0
                    local_noise_std = m['noise']
            
            # 3. Final SPL calculation
            # Use 50dB as a quiet floor, energy adds logarithmically
            spl = 50 + 10 * np.log10(base_noise_energy + 1e-5) - (local_alpha * 10) + (local_h_w * 2)
            
            # Make variance depend on buildings - more buildings = more scattering = more uncertainty
            building_influence = sum(1 for b in buildings if abs(b['x']-i) <= 1 and abs(b['y']-j) <= 1)
            dynamic_std = local_noise_std * (1.0 + 0.5 * building_influence)
            
            noise_samples = spl + np.random.normal(0, dynamic_std, 100)
            
            spl_map[i, j] = np.mean(noise_samples)
            var_map[i, j] = np.std(noise_samples)
            
    return jsonify({
        "spl": spl_map.tolist(),
        "variance": var_map.tolist()
    })

@app.route('/api/planner/suggest', methods=['POST'])
@app.route('/planner/suggest', methods=['POST'])
def planner_suggest():
    """
    Suggests improvements based on high SPL or high Variance.
    Avoids suggesting on top of existing sources or buildings.
    """
    data = request.json
    spl_map = np.array(data.get('spl'))
    var_map = np.array(data.get('variance'))
    sources = data.get('sources', [])
    buildings = data.get('buildings', [])
    
    source_locs = set((s['x'], s['y']) for s in sources)
    building_locs = set((b['x'], b['y']) for b in buildings)
    
    suggestions = []
    
    # 1. Identify high noise zones (above 70dB) that aren't sources
    high_noise = np.where(spl_map > 70)
    for i, j in zip(high_noise[0], high_noise[1]):
        if (i, j) not in source_locs and (i, j) not in building_locs:
            # Suggest a barrier adjacent to sources to block noise
            for si, sj in source_locs:
                if abs(si-i) <= 1 and abs(sj-j) <= 1:
                    suggestions.append({
                        "x": int(i), "y": int(j),
                        "type": "barrier",
                        "reason": f"High Noise Exposure ({round(spl_map[i,j], 1)} dB) near source"
                    })
                    break
        if len(suggestions) >= 3: break

    # 2. Identify high uncertainty zones
    if len(suggestions) < 3:
        high_var = np.where(var_map > 3.0)
        for i, j in zip(high_var[0], high_var[1]):
            if (i, j) not in source_locs and (i, j) not in building_locs:
                suggestions.append({
                    "x": int(i), "y": int(j),
                    "type": "vegetation",
                    "reason": "Unpredictable sound scattering zone"
                })
            if len(suggestions) >= 5: break
        
    return jsonify({"suggestions": suggestions})

@app.route('/api/simulate', methods=['POST'])
@app.route('/simulate', methods=['POST'])
def run_simulation():
    try:
        data = request.json
        num_rays = int(data.get('num_rays', 1000))
        max_bounces = int(data.get('max_bounces', 10))
        
        # 2. Configure Simulation using our unified engine
        # Lazy initialize mesh to avoid cold start issues
        scene_mesh = create_irregular_room()
        
        materials_path = os.path.join(project_root, "materials", "config.json")
        sim = MonteCarloSimulation(
            scene_mesh=scene_mesh,
            num_rays=num_rays,
            max_bounces=max_bounces,
            materials_path=materials_path
        )
        
        # Source at center of the L-shape
        source_pos = [5, 5, 2]
        
        # 3. Execute Simulation (Monte Carlo + Markov)
        paths, impulse_response = sim.run(source_pos)
        
        # 4. Generate Plots as Base64 strings
        ray_plot_b64 = visualize_ray_paths(paths)
        ir_plot_b64 = plot_impulse_response(impulse_response)
        heatmap_b64 = generate_heatmap(paths)
        
        # 5. Calculate Stats
        total_data_points = len(impulse_response)
        avg_energy = np.mean([er[1] for er in impulse_response]) if impulse_response else 0
        
        return jsonify({
            "status": "success",
            "stats": {
                "num_rays": num_rays,
                "max_bounces": max_bounces,
                "data_points": total_data_points,
                "avg_energy": round(float(avg_energy), 4)
            },
            "plots": {
                "ray_paths": f"data:image/png;base64,{ray_plot_b64}",
                "impulse_response": f"data:image/png;base64,{ir_plot_b64}",
                "heatmap": f"data:image/png;base64,{heatmap_b64}"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
