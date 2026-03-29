import numpy as np

class MarkovAcousticModel:
    """
    Markov Chain based acoustic propagation model.
    Each surface interaction is a probabilistic state transition.
    """
    def __init__(self, material_db):
        self.material_db = material_db

    def next_state(self, ray, surface_material):
        """
        Calculates the next state of a ray after interaction with a surface.
        
        States:
        - reflection: Ray continues with reflected direction
        - scattering: Ray continues with random direction
        - absorption: Ray energy becomes zero (terminated)
        """
        if surface_material not in self.material_db:
            # Default fallback if material is unknown
            probs = {"reflection": 0.8, "absorption": 0.1, "scattering": 0.1}
        else:
            probs = self.material_db[surface_material]

        actions = list(probs.keys())
        probabilities = list(probs.values())
        
        # Sample action based on Markov transition probabilities
        action = np.random.choice(actions, p=probabilities)

        return action

def reflect_vector(incident, normal):
    """Calculates the reflection vector."""
    return incident - 2 * np.dot(incident, normal) * normal

def scatter_vector(normal):
    """Calculates a random scattering vector in the hemisphere of the normal."""
    # Simple lambertian scattering
    phi = np.random.uniform(0, 2 * np.pi)
    cos_theta = np.sqrt(np.random.uniform(0, 1))
    sin_theta = np.sqrt(1 - cos_theta**2)
    
    # Local coordinate system
    z = normal
    x = np.array([1, 0, 0]) if abs(normal[0]) < 0.9 else np.array([0, 1, 0])
    y = np.cross(z, x)
    x = np.cross(y, z)
    
    return x * sin_theta * np.cos(phi) + y * sin_theta * np.sin(phi) + z * cos_theta
