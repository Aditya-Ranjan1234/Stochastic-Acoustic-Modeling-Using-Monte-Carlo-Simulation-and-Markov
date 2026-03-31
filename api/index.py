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
        "barrier": {"alpha": 0.9, "noise": 0.5},
        "hospital": {"alpha": 0.25, "noise": 1.2}
    }
    
    for i in range(grid_size):
        for j in range(grid_size):
            # 1. Calculate source-to-receiver noise with building attenuation
            base_noise_energy = 0
            for src in sources:
                src_x = src.get('x', 0)
                src_y = src.get('y', 0)
                src_intensity = src.get('intensity', 1000)
                dist = np.sqrt((src_x - i)**2 + (src_y - j)**2)
                
                # Check if any building is between source and current cell
                attenuation = 1.0
                for b in buildings:
                    bx = b.get('x', -1)
                    by = b.get('y', -1)
                    # Simple shadowing: if building is on the same line or very close
                    if min(src_x, i) <= bx <= max(src_x, i) and \
                       min(src_y, j) <= by <= max(src_y, j):
                        if (bx != i or by != j) and (bx != src_x or by != src_y):
                            mat_name = b.get('material', 'concrete')
                            mat_properties = materials.get(mat_name, materials['concrete'])
                            attenuation *= (1.0 - mat_properties.get('alpha', 0.2))
                
                # Inverse square law with shadowing
                base_noise_energy += (src_intensity * attenuation) / (dist**2 + 1.0)
            
            # 2. Local surface interactions
            local_alpha = 0.1
            local_h_w = 0.5
            local_noise_std = 1.0
            
            for b in buildings:
                bx = b.get('x', -1)
                by = b.get('y', -1)
                if bx == i and by == j:
                    mat_name = b.get('material', 'concrete')
                    m = materials.get(mat_name, materials['concrete'])
                    local_alpha = m.get('alpha', 0.2)
                    local_h_w = b.get('h', 5) / 5.0
                    local_noise_std = m.get('noise', 1.0)
            
            # 3. Final SPL calculation
            spl = 50 + 10 * np.log10(base_noise_energy + 1e-5) - (local_alpha * 10) + (local_h_w * 2)
            
            # Make variance depend on buildings
            building_influence = sum(1 for b in buildings if abs(b.get('x',-10)-i) <= 1 and abs(b.get('y',-10)-j) <= 1)
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

@app.route('/api/hospital/optimize', methods=['POST'])
def hospital_optimize():
    """
    Automated Advisor for Real-World Hospital Sites.
    Performs a global search for optimal ward and plant placements.
    """
    data = request.json
    site_id = data.get('site', 'kolkata')
    
    # Pre-defined sources for real-world sites
    presets = {
        'kolkata': {
            'buildings': [{"x": 0, "y": 2, "h": 5, "material": "concrete"}, {"x": 0, "y": 3, "h": 5, "material": "concrete"}, {"x": 0, "y": 6, "h": 5, "material": "concrete"}, {"x": 0, "y": 7, "h": 5, "material": "concrete"}, {"x": 0, "y": 8, "h": 5, "material": "hospital"}, {"x": 0, "y": 9, "h": 5, "material": "concrete"}, {"x": 1, "y": 3, "h": 5, "material": "concrete"}, {"x": 1, "y": 5, "h": 5, "material": "concrete"}, {"x": 1, "y": 6, "h": 5, "material": "concrete"}, {"x": 1, "y": 7, "h": 5, "material": "concrete"}, {"x": 1, "y": 8, "h": 5, "material": "concrete"}, {"x": 1, "y": 9, "h": 5, "material": "concrete"}, {"x": 2, "y": 4, "h": 5, "material": "concrete"}, {"x": 2, "y": 5, "h": 15, "material": "concrete"}, {"x": 2, "y": 6, "h": 12, "material": "concrete"}, {"x": 2, "y": 7, "h": 5, "material": "concrete"}, {"x": 2, "y": 8, "h": 5, "material": "concrete"}, {"x": 2, "y": 9, "h": 5, "material": "concrete"}, {"x": 3, "y": 2, "h": 5, "material": "concrete"}, {"x": 3, "y": 4, "h": 5, "material": "hospital"}, {"x": 3, "y": 6, "h": 5, "material": "concrete"}, {"x": 3, "y": 7, "h": 5, "material": "concrete"}, {"x": 3, "y": 8, "h": 5, "material": "concrete"}, {"x": 3, "y": 9, "h": 5, "material": "concrete"}, {"x": 4, "y": 2, "h": 5, "material": "concrete"}, {"x": 4, "y": 4, "h": 5, "material": "concrete"}, {"x": 4, "y": 6, "h": 5, "material": "concrete"}, {"x": 4, "y": 7, "h": 5, "material": "concrete"}, {"x": 4, "y": 8, "h": 5, "material": "concrete"}, {"x": 4, "y": 9, "h": 5, "material": "concrete"}, {"x": 5, "y": 1, "h": 5, "material": "concrete"}, {"x": 5, "y": 2, "h": 5, "material": "concrete"}, {"x": 5, "y": 3, "h": 5, "material": "concrete"}, {"x": 5, "y": 4, "h": 5, "material": "concrete"}, {"x": 5, "y": 7, "h": 5, "material": "concrete"}, {"x": 5, "y": 8, "h": 5, "material": "concrete"}, {"x": 5, "y": 9, "h": 5, "material": "concrete"}, {"x": 6, "y": 0, "h": 5, "material": "concrete"}, {"x": 6, "y": 2, "h": 5, "material": "concrete"}, {"x": 6, "y": 3, "h": 5, "material": "concrete"}, {"x": 6, "y": 4, "h": 5, "material": "concrete"}, {"x": 6, "y": 5, "h": 5, "material": "concrete"}, {"x": 6, "y": 7, "h": 5, "material": "concrete"}, {"x": 6, "y": 8, "h": 5, "material": "concrete"}, {"x": 6, "y": 9, "h": 5, "material": "concrete"}, {"x": 7, "y": 2, "h": 5, "material": "concrete"}, {"x": 7, "y": 3, "h": 5, "material": "concrete"}, {"x": 7, "y": 4, "h": 5, "material": "concrete"}, {"x": 7, "y": 5, "h": 5, "material": "concrete"}, {"x": 7, "y": 6, "h": 5, "material": "concrete"}, {"x": 7, "y": 7, "h": 5, "material": "concrete"}, {"x": 7, "y": 8, "h": 5, "material": "concrete"}, {"x": 7, "y": 9, "h": 5, "material": "hospital"}, {"x": 8, "y": 0, "h": 5, "material": "concrete"}, {"x": 8, "y": 1, "h": 5, "material": "concrete"}, {"x": 8, "y": 3, "h": 5, "material": "concrete"}, {"x": 8, "y": 4, "h": 5, "material": "concrete"}, {"x": 8, "y": 5, "h": 5, "material": "concrete"}, {"x": 8, "y": 6, "h": 5, "material": "concrete"}, {"x": 8, "y": 7, "h": 5, "material": "concrete"}, {"x": 8, "y": 8, "h": 5, "material": "concrete"}, {"x": 8, "y": 9, "h": 5, "material": "concrete"}, {"x": 9, "y": 1, "h": 5, "material": "concrete"}, {"x": 9, "y": 3, "h": 5, "material": "concrete"}, {"x": 9, "y": 4, "h": 5, "material": "concrete"}, {"x": 9, "y": 5, "h": 5, "material": "concrete"}, {"x": 9, "y": 6, "h": 5, "material": "concrete"}, {"x": 9, "y": 7, "h": 5, "material": "concrete"}, {"x": 9, "y": 8, "h": 5, "material": "concrete"}, {"x": 9, "y": 9, "h": 5, "material": "concrete"}],
            'sources': [{'x': 4, 'y': 7, 'intensity': 1500}, {'x': 8, 'y': 5, 'intensity': 1200}, {'x': 1, 'y': 9, 'intensity': 1000}]
        },
        'barcelona': {
            'buildings': [{"x": 0, "y": 2, "h": 15, "material": "concrete"}, {"x": 0, "y": 3, "h": 5, "material": "concrete"}, {"x": 0, "y": 4, "h": 15, "material": "concrete"}, {"x": 0, "y": 5, "h": 5, "material": "concrete"}, {"x": 0, "y": 6, "h": 5, "material": "concrete"}, {"x": 0, "y": 7, "h": 5, "material": "concrete"}, {"x": 1, "y": 2, "h": 15, "material": "concrete"}, {"x": 1, "y": 6, "h": 5, "material": "concrete"}, {"x": 2, "y": 0, "h": 15, "material": "concrete"}, {"x": 2, "y": 1, "h": 15, "material": "concrete"}, {"x": 2, "y": 2, "h": 15, "material": "concrete"}, {"x": 2, "y": 3, "h": 5, "material": "concrete"}, {"x": 2, "y": 4, "h": 15, "material": "concrete"}, {"x": 2, "y": 5, "h": 15, "material": "concrete"}, {"x": 2, "y": 6, "h": 5, "material": "concrete"}, {"x": 2, "y": 7, "h": 5, "material": "concrete"}, {"x": 2, "y": 8, "h": 5, "material": "concrete"}, {"x": 2, "y": 9, "h": 5, "material": "concrete"}, {"x": 3, "y": 0, "h": 15, "material": "concrete"}, {"x": 3, "y": 1, "h": 15, "material": "concrete"}, {"x": 3, "y": 2, "h": 5, "material": "concrete"}, {"x": 3, "y": 4, "h": 15, "material": "concrete"}, {"x": 3, "y": 5, "h": 5, "material": "concrete"}, {"x": 3, "y": 7, "h": 5, "material": "concrete"}, {"x": 3, "y": 8, "h": 5, "material": "concrete"}, {"x": 3, "y": 9, "h": 5, "material": "concrete"}, {"x": 4, "y": 0, "h": 15, "material": "concrete"}, {"x": 4, "y": 1, "h": 15, "material": "concrete"}, {"x": 4, "y": 2, "h": 5, "material": "concrete"}, {"x": 4, "y": 3, "h": 5, "material": "concrete"}, {"x": 4, "y": 4, "h": 5, "material": "concrete"}, {"x": 4, "y": 7, "h": 15, "material": "concrete"}, {"x": 4, "y": 8, "h": 15, "material": "concrete"}, {"x": 4, "y": 9, "h": 15, "material": "concrete"}, {"x": 5, "y": 0, "h": 15, "material": "concrete"}, {"x": 5, "y": 2, "h": 15, "material": "concrete"}, {"x": 5, "y": 3, "h": 5, "material": "concrete"}, {"x": 5, "y": 4, "h": 15, "material": "concrete"}, {"x": 5, "y": 6, "h": 5, "material": "concrete"}, {"x": 5, "y": 7, "h": 15, "material": "concrete"}, {"x": 5, "y": 9, "h": 15, "material": "concrete"}, {"x": 6, "y": 0, "h": 15, "material": "concrete"}, {"x": 6, "y": 2, "h": 5, "material": "concrete"}, {"x": 6, "y": 4, "h": 15, "material": "concrete"}, {"x": 6, "y": 8, "h": 15, "material": "concrete"}, {"x": 7, "y": 0, "h": 15, "material": "concrete"}, {"x": 7, "y": 2, "h": 15, "material": "concrete"}, {"x": 7, "y": 3, "h": 5, "material": "concrete"}, {"x": 7, "y": 4, "h": 15, "material": "concrete"}, {"x": 7, "y": 5, "h": 5, "material": "concrete"}, {"x": 7, "y": 6, "h": 5, "material": "concrete"}, {"x": 7, "y": 7, "h": 5, "material": "concrete"}, {"x": 7, "y": 8, "h": 5, "material": "concrete"}, {"x": 7, "y": 9, "h": 15, "material": "concrete"}, {"x": 8, "y": 2, "h": 5, "material": "concrete"}, {"x": 8, "y": 3, "h": 5, "material": "concrete"}, {"x": 8, "y": 7, "h": 5, "material": "concrete"}, {"x": 9, "y": 3, "h": 5, "material": "concrete"}, {"x": 9, "y": 4, "h": 5, "material": "concrete"}, {"x": 9, "y": 6, "h": 15, "material": "concrete"}, {"x": 9, "y": 7, "h": 15, "material": "concrete"}],
            'sources': [{'x': 3, 'y': 3, 'intensity': 1200}, {'x': 7, 'y': 6, 'intensity': 1000}]
        }
    }
    
    site = presets.get(site_id, presets['kolkata'])
    buildings = site['buildings']
    sources = site['sources']
    
    # 1. Compute Base Noise Map (20x20)
    grid_size = 20
    spl_map = np.full((grid_size, grid_size), 35.0) # 35dB hospital baseline
    
    # Pre-scale buildings and sources to the 20x20 grid
    # Original map is 10x10, we are now 20x20 (x2 scale)
    for y in range(grid_size):
        for x in range(grid_size):
            total_energy = 0
            for s in sources:
                # Source coordinates (already in 10x10 space)
                sx, sy = s['x'] * 2, s['y'] * 2
                
                # Distance in grid units
                dist = np.sqrt((sx - x)**2 + (sy - y)**2)
                
                # Attenuation Logic (Inverse Square Law + Shadowing)
                attenuation = 1.0
                
                # RAY-CASTING for building shadows (Simplified for performance)
                for b in buildings:
                    bx, by = b.get('x', -1) * 2, b.get('y', -1) * 2
                    bh = b.get('h', 5)
                    # If building is between source and point
                    if (min(sx, x) <= bx <= max(sx, x)) and (min(sy, y) <= by <= max(sy, y)):
                        # Simple Diffraction: Further reduction if building is high
                        attenuation *= (0.2 if bh > 10 else 0.5) 

                # Invers Square Law (NMPB-Road style approximation)
                energy = (s.get('intensity', 1500) * attenuation) / (4 * np.pi * (dist**2 + 0.5))
                total_energy += energy
            
            # SPL conversion with sensitive range
            if total_energy > 0:
                spl_map[y, x] = 30 + 10 * np.log10(total_energy + 1e-6)

    # 2. Automated Search for Ideal Placements
    # Find Local Minima for multiple "Ideal Wards" (Top 3 non-adjacent)
    ideal_wards = []
    # Simplified local minima search: pick the quietest cells that are at least 5 units apart
    temp_spl = spl_map.copy()
    for _ in range(3):
        idx = np.argmin(temp_spl)
        wy, wx = idx // grid_size, idx % grid_size
        spl_val = temp_spl[wy, wx]
        if spl_val > 60: break # Don't place wards in loud areas
        
        ideal_wards.append({"x": int(wx // 2), "y": int(wy // 2), "spl": round(float(spl_val), 1)})
        
        # Zero-out neighborhood to find the NEXT local minimum
        y_min, y_max = max(0, wy-4), min(grid_size, wy+5)
        x_min, x_max = max(0, wx-4), min(grid_size, wx+5)
        temp_spl[y_min:y_max, x_min:x_max] = 100 # High value to exclude
    
    # 3. Distributed Shielding (Plants)
    # For each ward, place a buffer halfway between it and the 2 most intense sources
    ideal_plants = []
    sorted_sources = sorted(sources, key=lambda s: s.get('intensity', 0), reverse=True)
    
    for w in ideal_wards:
        wx, wy = w['x'], w['y']
        for s in sorted_sources[:2]: # Only shield the 2 loudest sources per ward
            sx, sy = s['x'], s['y']
            # Midpoint for shielding
            px, py = (sx + wx) // 2, (sy + wy) // 2
            # Add if not duplicate
            if not any(p['x'] == px and p['y'] == py for p in ideal_plants):
                ideal_plants.append({"x": int(px), "y": int(py)})

    # All preset sources are returned as Signal Recommendations for traffic control
    ideal_signals = [{"x": s['x'], "y": s['y']} for s in sorted_sources]

    suggestions = []
    for i, w in enumerate(ideal_wards):
        suggestions.append({
            "label": f"Medical Zone {chr(65+i)}", 
            "reason": f"Safe zone detected at ({w['x']}, {w['y']}) with sound pressure of {w['spl']} dB."
        })
    
    if len(ideal_plants) > 0:
        suggestions.append({
            "label": "Buffer Phase 1",
            "reason": f"Strategic planting of {len(ideal_plants)} acoustic screens to protect the identified zones."
        })
    
    suggestions.append({
        "label": "Source Control",
        "reason": f"Active monitoring of {len(ideal_signals)} local noise emitters detected in vicinity."
    })

    return jsonify({
        "spl_map": spl_map.tolist(),
        "quietness_index": round(float(100 - np.mean([w['spl'] for w in ideal_wards])), 1) if ideal_wards else 0,
        "optimal_wards": ideal_wards,
        "optimal_plants": ideal_plants,
        "optimal_signals": ideal_signals,
        "suggestions": suggestions
    })

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
