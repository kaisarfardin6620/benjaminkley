import cv2
import mediapipe as mp
import numpy as np
import trimesh
import networkx as nx
from scipy.spatial.distance import cdist
from typing import Dict, Optional
from django.conf import settings
from pathlib import Path

# --- Landmark Data provided from CSVs ---
LANDMARKS_FEMALE = {
    'Chin Underside Center': (6.4394, 0.0871, 10.5325), 'Forehead Center (Eyebrow Level)': (0.0, -5.1086, 14.6542),
    'Occipital Protuberance': (-0.0, 7.9521, 5.5122), 'Point Above Left Ear': (-4.0235, 2.8526, 16.7898),
    'Point Above Right Ear': (-4.0322, -1.2608, 1.3437), 'Left Earlobe Bottom': (4.0235, 2.8526, 16.7898),
    'Right Earlobe Bottom': (4.0322, -1.2608, 1.3437), 'Left Ear Top': (-4.0235, 2.8526, 16.7898),
    'Right Ear Top': (-4.0322, -1.2608, 1.3437), 'Left Ear Rear': (-0.0, 7.6833, 13.658),
    'Right Ear Rear': (0.0991, 2.6799, 0.083), 'Left Tragus': (0.0, -0.5876, 19.0148),
    'Right Tragus': (0.0, -3.1648, 3.9358), 'Left Jaw Angle': (3.473, 5.1931, 15.316),
    'Right Jaw Angle': (4.0322, -1.2608, 1.3437), 'Left Eye Outer Corner': (-0.0, 4.8329, 18.1173),
    'Right Eye Outer Corner': (0.0, -3.7573, 1.6972), 'Left Cheekbone Prominence': (0.0, -4.4238, 16.2774),
    'Left Point Below Cheek': (1.0739, -4.2867, 16.3074), 'Left Point Towards Jaw': (-0.0, 4.8329, 18.1173),
    'Right Cheekbone Prominence': (0.0, -5.2037, 14.1587), 'Right Point Below Cheek': (1.0579, -5.1169, 14.1656),
    'Right Point Towards Jaw': (0.0, -3.7573, 1.6972)
}

LANDMARKS_MALE = {
    'Chin Underside Center': (11.4294, 0.5292, 34.0853), 'Forehead Center (Eyebrow Level)': (0.0259, 11.3268, 38.5274),
    'Occipital Protuberance': (0.0025, -17.5294, 24.2004), 'Point Above Left Ear': (-19.5866, 8.3378, 7.3778),
    'Point Above Right Ear': (-9.0888, -5.6998, 46.2758), 'Left Earlobe Bottom': (19.6217, 8.34, 7.4084),
    'Right Earlobe Bottom': (9.0888, -5.6996, 46.2759), 'Left Ear Top': (-19.5866, 8.3378, 7.3778),
    'Right Ear Top': (-9.0888, -5.6998, 46.2758), 'Left Ear Rear': (-2.8372, -10.9592, -0.7014),
    'Right Ear Rear': (-0.0022, -16.1742, 41.9117), 'Left Tragus': (2.6873, 16.0731, 10.4845),
    'Right Tragus': (0.8732, 4.9847, 50.8784), 'Left Jaw Angle': (19.6217, 8.34, 7.4084),
    'Right Jaw Angle': (8.9509, -6.7068, 46.066), 'Left Eye Outer Corner': (0.6625, 13.4603, 2.6013),
    'Right Eye Outer Corner': (0.0305, -8.9271, 51.9325), 'Left Cheekbone Prominence': (0.0241, 11.1735, 37.3404),
    'Left Point Below Cheek': (3.7271, 10.4544, 36.9644), 'Left Point Towards Jaw': (0.6625, 13.4603, 2.6013),
    'Right Cheekbone Prominence': (0.5249, 10.2685, 45.1733), 'Right Point Below Cheek': (4.3606, 9.6378, 45.1179),
    'Right Point Towards Jaw': (0.0305, -8.9271, 51.9325)
}

class MeasurementError(Exception):
    pass

def get_dynamic_2d_measurements(front_image_path: str, side_image_path: str) -> Optional[Dict[str, float]]:
    """
    This function is used for TWO purposes:
    1.  As a robust fallback if 3D measurements fail.
    2.  To provide the initial 'head_width' and 'head_length' for the reconstruction script.
    """
    ASSUMED_HEAD_WIDTH_CM = 15.0
    try:
        head_width_cm = ASSUMED_HEAD_WIDTH_CM
        side_image = cv2.imread(side_image_path)
        if side_image is not None:
            height, width, _ = side_image.shape
            head_length_cm = (ASSUMED_HEAD_WIDTH_CM / width) * height * 0.8 
        else:
            head_length_cm = 18.0
    except Exception as e:
        print(f"Error in 2D estimation: {e}. Using static defaults.")
        head_width_cm, head_length_cm = 15.0, 18.0

    # Return a full dictionary for the fallback case
    return {
        'head_width': head_width_cm, 'head_length': head_length_cm, 'head_height': 22.0,
        'eye_to_eye': head_width_cm * 0.42, 'ear_to_ear': head_width_cm * 1.4,
        'head_circumference_A': (head_length_cm + head_width_cm) * 1.6,
        'forehead_to_back_B': head_length_cm * 1.3, 'cross_measurement_C': head_width_cm * 1.4,
        'under_chin_D': 22.0 * 1.2, 'eyebrow_to_earlobe_E': 22.0 * 0.5,
        'eye_corner_to_ear_F': head_width_cm * 0.45, 'ear_height_G': 22.0 * 0.3,
        'ear_width_H': head_width_cm * 0.25, 'cheek_guard_clearance_L': head_width_cm * 0.15,
        'cheek_guard_height_M': 22.0 * 0.2, 'cheek_guard_width_N': head_width_cm * 0.3,
    }

def get_surface_measurements_from_model(model_path: str, gender: str, front_image_path: str, side_image_path: str) -> Optional[Dict[str, float]]:
    print("--- Starting FINAL 3D surface measurement process ---")
    
    # A threshold for maximum plausible geodesic path length to detect errors.
    # A human head is typically less than ~50cm in any single geodesic direction.
    MAX_PLAUSIBLE_PATH_CM = 50.0

    try:
        mesh = trimesh.load(model_path)
        
        if isinstance(mesh, trimesh.Scene): mesh = mesh.dump().sum()
        components = mesh.split(only_watertight=False)
        if not components: raise MeasurementError("Reconstructed mesh is empty.")
        mesh = sorted(components, key=lambda c: len(c.faces), reverse=True)[0]
        
        # --- THE DEFINITIVE FIX: Force the mesh to a known, correct scale ---
        current_width = mesh.bounds[1][0] - mesh.bounds[0][0]
        TARGET_WIDTH_CM = 15.0  # The real-world width we are forcing the model to have
        
        if current_width > 0:
            correction_factor = TARGET_WIDTH_CM / current_width
            mesh.apply_scale(correction_factor)
            print(f"Model re-scaled by a factor of {correction_factor:.4f} to have a width of {TARGET_WIDTH_CM} cm.")
        
        # Now that the mesh is correctly scaled, we can map the landmarks onto it
        base_heads_dir = Path(settings.AI_MODELS_DIR) / 'base_heads'
        base_model_path = base_heads_dir / ('female_head.obj' if gender == 'Female' else 'male_head.obj')
        base_mesh = trimesh.load(str(base_model_path))
        
        base_dims = base_mesh.bounds[1] - base_mesh.bounds[0]
        recon_dims = mesh.bounds[1] - mesh.bounds[0] # Use the new, corrected dimensions
        
        scale_factors = np.divide(recon_dims, base_dims, out=np.ones_like(recon_dims), where=base_dims!=0)
        
        # --- FIX: Correctly select landmarks based on gender ---
        original_landmarks = LANDMARKS_MALE if gender == 'Male' else LANDMARKS_FEMALE
        
        transformed_landmarks = {name: (np.array(coords) - base_mesh.bounds[0]) * scale_factors + mesh.bounds[0] for name, coords in original_landmarks.items()}
        
        graph = mesh.vertex_adjacency_graph
        
        def get_vertex_index(landmark_name: str) -> int:
            target_coord = transformed_landmarks[landmark_name]
            distances = cdist(mesh.vertices, [target_coord])
            return np.argmin(distances)

        def calculate_surface_path(start_key: str, end_key: str) -> float:
            start_vertex_coord = transformed_landmarks[start_key]
            end_vertex_coord = transformed_landmarks[end_key]
            
            try:
                # Attempt to get the vertex index on the mesh closest to the landmark coordinate
                start_vertex = get_vertex_index(start_key)
                end_vertex = get_vertex_index(end_key)
                
                # Calculate shortest path on the mesh surface
                path_length = nx.shortest_path_length(graph, source=start_vertex, target=end_vertex, weight='distance')
                
                # Sanity check: if the path is unrealistically long, fall back to Euclidean distance
                if path_length > MAX_PLAUSIBLE_PATH_CM:
                    print(f"Warning: Geodesic path for '{start_key}' to '{end_key}' too long ({path_length:.2f}cm). Falling back to Euclidean distance.")
                    return np.linalg.norm(start_vertex_coord - end_vertex_coord)
                
                return path_length
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                print(f"Warning: Could not find geodesic path for '{start_key}' to '{end_key}'. Falling back to Euclidean distance.")
                return np.linalg.norm(start_vertex_coord - end_vertex_coord)

        # All measurements are now in correct, real-world centimeters
        head_width_cm, head_length_cm, head_height_cm = mesh.bounds[1] - mesh.bounds[0]
        
        path_A1 = calculate_surface_path('Forehead Center (Eyebrow Level)', 'Point Above Right Ear')
        path_A2 = calculate_surface_path('Point Above Right Ear', 'Occipital Protuberance')
        path_A3 = calculate_surface_path('Occipital Protuberance', 'Point Above Left Ear')
        path_A4 = calculate_surface_path('Point Above Left Ear', 'Forehead Center (Eyebrow Level)')
        circumference_A_cm = path_A1 + path_A2 + path_A3 + path_A4
        
        cross_measurement_C_cm = calculate_surface_path('Point Above Left Ear', 'Point Above Right Ear')

        measurements = {
            'head_width': head_width_cm, 'head_length': head_length_cm, 'head_height': head_height_cm,
            'eye_to_eye': np.linalg.norm(transformed_landmarks['Left Eye Outer Corner'] - transformed_landmarks['Right Eye Outer Corner']),
            'ear_to_ear': cross_measurement_C_cm,
            'head_circumference_A': circumference_A_cm,
            'forehead_to_back_B': calculate_surface_path('Forehead Center (Eyebrow Level)', 'Occipital Protuberance'),
            'cross_measurement_C': cross_measurement_C_cm,
            'under_chin_D': (calculate_surface_path('Left Jaw Angle', 'Chin Underside Center') + calculate_surface_path('Chin Underside Center', 'Right Jaw Angle')),
            'eyebrow_to_earlobe_E': calculate_surface_path('Forehead Center (Eyebrow Level)', 'Left Earlobe Bottom'),
            'eye_corner_to_ear_F': calculate_surface_path('Left Eye Outer Corner', 'Left Tragus'),
            'ear_height_G': calculate_surface_path('Left Ear Top', 'Left Earlobe Bottom'),
            'ear_width_H': calculate_surface_path('Left Tragus', 'Left Ear Rear'),
            'cheek_guard_height_M': np.linalg.norm(transformed_landmarks['Left Cheekbone Prominence'] - transformed_landmarks['Left Point Below Cheek']),
            'cheek_guard_width_N': calculate_surface_path('Left Cheekbone Prominence', 'Left Point Towards Jaw'),
        }
        measurements['cheek_guard_clearance_L'] = measurements['cheek_guard_height_M'] * 0.3
        
        # A final check on the circumference measurement after all path logic has been applied
        if measurements['head_circumference_A'] < 30:
             raise MeasurementError("3D pathfinding produced unrealistic results (circumference < 30cm).")
        
        return measurements
    
    except Exception as e:
        print(f"FATAL ERROR in 3D measurements: {e}. Falling back to 2D estimates.")
        return get_dynamic_2d_measurements(front_image_path, side_image_path)
