# Acoustic Markov Lab: Stochastic Urban Modeling

A comprehensive research demonstration of **Stochastic Acoustic Modeling** using Monte Carlo simulations and Markov Processes for irregular 3D geometries.

## 🚀 Overview
This project explores the intersection of geometric ray-tracing and probabilistic state transitions to simulate sound propagation in complex urban environments and irregular architectural spaces.

## 🧠 Key Research Concepts
- **Monte Carlo Ray Tracing**: Tracing thousands of stochastic rays to approximate diffuse sound fields in non-convex geometries.
- **Markovian Transitions**: Treating surface interactions (Reflection, Scattering, Absorption) as probabilistic state changes defined by a transition matrix.
- **Street Canyon Dynamics**: Modeling the relationship between H/W aspect ratios and Sound Pressure Level (SPL) through stationary distribution analysis.
- **Urban Stochasticity**: Analyzing how natural variations in city block geometry and materials affect acoustic uncertainty (95% Confidence Intervals).

## 🛠️ Project Structure
- `/engine`: Core Monte Carlo simulation logic using `trimesh`.
- `/markov`: Markov Chain transition models and material databases.
- `/visualization`: 3D trajectory plotting, heatmaps, and impulse response generation.
- `/static`: Premium Glassmorphism web interface for interactive experimentation.

## 💻 Installation & Usage

### Prerequisites
- Python 3.10+
- Existing virtual environment (venv)

### Running the Dashboard
1. Ensure the required dependencies are installed:
   ```bash
   pip install flask numpy trimesh scipy matplotlib networkx manifold3d
   ```
2. Start the Flask server:
   ```bash
   python app.py
   ```
3. Open `http://localhost:5001` in your browser.

## 📊 Dashboard Tabs
1. **3D Simulation**: High-fidelity ray-tracing in irregular 3D mesh rooms.
2. **Street Canyon**: Interactive Markov matrix visualizer for urban canyons.
3. **Convergence**: Real-time demonstration of the Law of Large Numbers in acoustics.
4. **Urban Grid**: Stochastic SPL mapping across a 4x4 city block grid.

## ⚖️ License
Research Project - Academic Use Only.
