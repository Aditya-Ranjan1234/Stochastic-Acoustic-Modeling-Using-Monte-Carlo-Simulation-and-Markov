# In-Depth Research Documentation: Stochastic Acoustic Modeling
## 1. Introduction to Acoustic Modeling
Acoustic modeling is the science of predicting how sound waves behave in an environment. Traditionally, this is done using **Deterministic Models**, where every reflection follows a fixed, predictable path (like a billiard ball hitting a wall).

While this works for simple box-shaped rooms, it fails in the real world where:
- Walls have texture and cause **Scattering**.
- Geometries are **Irregular** (L-shapes, curved halls).
- Environments are **Open** (Urban streets, canyons).

This project introduces a **Hybrid Stochastic-Markov Approach** to solve these complexities efficiently.

---

## 2. Existing Systems: What do they use?
Industry-standard tools like **ODEON**, **EASE**, or **COMSOL** typically use one of two methods:

1.  **Image Source Method**: Creates "virtual sources" for every reflection.
    - *Problem*: Becomes computationally impossible (exponential growth) after a few reflections.
2.  **Deterministic Ray Tracing**: Traces a finite number of rays.
    - *Problem*: Often ignores "diffuse" sound (scattering) or requires massive computing power to handle irregular shapes.

### How this project helps:
By using **Monte Carlo Sampling** and **Markov Processes**, we replace heavy computation with **Probability**. Instead of calculating every single physical interaction, we sample the most likely paths. This makes it:
- **Faster**: Runs on a web server in seconds.
- **Realistic**: Naturally handles sound scattering and absorption probabilities.
- **Scalable**: Can model a single room or an entire city grid using the same mathematical framework.

---

## 3. Tab-by-Tab Breakdown: How it works & Why it's unique

### **Tab 1: 3D Monte Carlo Simulation**
*   **What it is**: A high-fidelity 3D physics engine that traces sound rays in an irregular room.
*   **How it works**:
    - **Monte Carlo Sampling**: We launch $N$ rays (e.g., 1000) in random directions from a source.
    - **Trimesh Intersection**: We use a 3D library (Trimesh) to find exactly where each ray hits a wall.
    - **Energy Decay**: Every time a ray hits a surface, it loses energy based on that material's **Absorption Coefficient**.
*   **Unique Feature**: It generates an **Impulse Response (IR)**. This is the "Acoustic Fingerprint" of a room, showing exactly how sound energy decays over time.

### **Tab 2: Street Canyon Simulator**
*   **What it is**: A specialized model for urban environments (streets between tall buildings).
*   **How it works**:
    - **Markov State Transitions**: We define 5 states: *Left Facade, Right Facade, Ground, Sky, and Receiver*.
    - **Transition Matrix (P)**: A 5x5 matrix calculates the probability of sound jumping from one surface to another.
    - **Stationary Distribution (π)**: We solve the equation $\pi P = \pi$. This finds the "equilibrium" state of noise.
*   **Unique Feature**: It doesn't trace rays. It uses **Linear Algebra** to predict long-term noise levels. It’s mathematically equivalent to tracing a ray an infinite number of times, but takes milliseconds to solve.

### **Tab 3: Convergence (LLN)**
*   **What it is**: A mathematical "sanity check" for the Monte Carlo method.
*   **How it works**:
    - It runs a simulation repeatedly, adding more and more samples (N).
    - It plots the **Running Mean** and the **Confidence Interval (CI)**.
*   **Unique Feature**: It proves the **Law of Large Numbers (LLN)**. It shows the researcher: *"If you want a result accurate to ±0.5 dB, you need exactly 5,000 rays."* It turns guesswork into statistical certainty.

### **Tab 4: 2D Urban Grid Heatmap**
*   **What it is**: A macro-scale tool for city planners.
*   **How it works**:
    - It divides a city into a 4x4 grid.
    - Each cell runs its own Markov model based on its "Profile" (e.g., *Dense Urban* vs. *Suburban*).
    - It generates two maps: **Mean Noise (SPL)** and **Uncertainty (Variance)**.
*   **Unique Feature**: Most noise maps only show the average noise. Ours shows the **Uncertainty**. If a cell has high uncertainty, it tells the planner that the noise there is highly unpredictable due to the building layout.

---

## 4. Scientific Uniqueness
1.  **Probabilistic Coupling**: We don't just treat walls as objects; we treat them as **States in a Markov Chain**.
2.  **Geometric Agnosticism**: Because we use Trimesh, the model doesn't care if the room is a cube or a complex cathedral.
3.  **Real-Time Feedback**: By combining Python (Fast Math) with a modern Web UI, researchers can tweak a parameter (like facade absorption) and see the city-wide impact instantly.

---

## 5. Applications
- **Architectural Acoustics**: Designing auditoriums with perfect reverb.
- **Smart City Planning**: Placing noise barriers in the most effective locations.
- **Indoor Navigation**: Using acoustic "fingerprints" for GPS-denied environments.
- **Environmental Impact**: Predicting how a new skyscraper will reflect traffic noise into a nearby park.
