import numpy as np
import json
import os
import trimesh
from markov.model import MarkovAcousticModel, reflect_vector, scatter_vector

class MonteCarloSimulation:
    """
    Monte Carlo + Markov Engine for irregular geometries.
    Uses trimesh for real ray-mesh intersections.
    """
    def __init__(self, scene_mesh, num_rays=1000, max_bounces=10, materials_path=None):
        self.mesh = scene_mesh
        self.num_rays = num_rays
        self.max_bounces = max_bounces
        
        # Load Markov material database
        if materials_path and os.path.exists(materials_path):
            with open(materials_path, 'r') as f:
                self.material_db = json.load(f)
        else:
            self.material_db = {
                "default": {"reflection": 0.8, "absorption": 0.1, "scattering": 0.1}
            }
            
        self.markov_model = MarkovAcousticModel(self.material_db)
        
        # Robust ray-mesh intersector initialization
        try:
            # Try to use pyembree if available for high performance
            import embreex
            self.intersector = trimesh.ray.ray_pyembree.RayMeshIntersector(self.mesh)
        except (ImportError, Exception):
            # Fallback to the native trimesh triangle intersector (no external dependencies)
            self.intersector = trimesh.ray.ray_triangle.RayMeshIntersector(self.mesh)

    def run(self, source_pos):
        """
        Main simulation loop using Monte Carlo sampling and Markov state transitions.
        """
        paths = []
        impulse_response = []
        
        source_pos = np.array(source_pos)
        
        for _ in range(self.num_rays):
            # Monte Carlo sampling: Uniform spherical distribution
            phi = np.random.uniform(0, 2 * np.pi)
            cos_theta = np.random.uniform(-1, 1)
            sin_theta = np.sqrt(1 - cos_theta**2)
            direction = np.array([sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta])
            
            ray_pos = source_pos.copy()
            ray_path = [ray_pos.tolist()]
            energy = 1.0
            total_dist = 0.0
            
            for bounce in range(self.max_bounces):
                if energy < 0.01: break
                
                # Ray-Mesh Intersection
                index_tri, index_ray, locations = self.intersector.intersects_id(
                    ray_origins=[ray_pos],
                    ray_directions=[direction],
                    return_locations=True
                )
                
                if len(locations) == 0:
                    break
                
                # Get closest hit
                hit_point = locations[0]
                hit_dist = np.linalg.norm(hit_point - ray_pos)
                
                if hit_dist < 1e-4: # Prevent self-intersection
                    # Try finding a further intersection if we are stuck on the surface
                    if len(locations) > 1:
                        hit_point = locations[1]
                        hit_dist = np.linalg.norm(hit_point - ray_pos)
                    else:
                        break

                normal = self.mesh.face_normals[index_tri[0]]
                
                # Update position and distance
                ray_pos = hit_point
                total_dist += hit_dist
                ray_path.append(ray_pos.tolist())
                
                # Determine material (procedural for this demo)
                material = "concrete" # Default
                if abs(normal[2]) > 0.9: material = "concrete" # Floor/Ceiling
                elif abs(normal[0]) > 0.9: material = "brick" # Side walls
                else: material = "wood"
                
                # Markov state transition
                action = self.markov_model.next_state(None, material)
                
                if action == "absorption":
                    energy = 0
                    break
                elif action == "scattering":
                    direction = scatter_vector(normal)
                    energy *= 0.8
                else: # reflection
                    direction = reflect_vector(direction, normal)
                    energy *= 0.95
                
                # Speed of sound c = 343 m/s
                arrival_time = total_dist / 343.0
                impulse_response.append((arrival_time, energy))
                
            paths.append(ray_path)
            
        return paths, impulse_response

def create_irregular_room():
    """
    Creates an L-shaped room (irregular geometry) for acoustic modeling.
    """
    # Create two boxes and combine them to make an L-shape
    box1 = trimesh.creation.box(extents=[10, 10, 4])
    box1.apply_translation([5, 5, 2])
    
    box2 = trimesh.creation.box(extents=[6, 15, 4])
    box2.apply_translation([13, 2.5, 2])
    
    room = trimesh.boolean.union([box1, box2])
    return room
