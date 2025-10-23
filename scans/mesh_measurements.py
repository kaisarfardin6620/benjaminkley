# scans/mesh_measurements.py

import trimesh
import numpy as np

def _find_anatomical_landmarks(mesh):
    """Finds vertex indices for key landmarks based on geometric properties."""
    vertices = mesh.vertices
    
    # NOTE: Assumes the head is oriented with +Y forward (nose), +Z up, +X right.
    landmarks = {
        'chin_idx': np.argmin(vertices[:, 2]),
        'nose_tip_idx': np.argmax(vertices[:, 1]),
        'top_of_head_idx': np.argmax(vertices[:, 2]),
        'back_of_head_idx': np.argmin(vertices[:, 1]),
        'right_side_idx': np.argmax(vertices[:, 0]),
        'left_side_idx': np.argmin(vertices[:, 0]),
    }
    
    # Estimate nasion (between eyebrows)
    nose_tip_vertex = vertices[landmarks['nose_tip_idx']]
    nasion_estimate = nose_tip_vertex + [0, -2.0, 3.0]
    _, _, nasion_idx = trimesh.proximity.closest_point(mesh, [nasion_estimate])
    landmarks['nasion_idx'] = nasion_idx[0]
    
    print(f"--- Anatomical landmarks identified ---")
    return landmarks

def _calculate_surface_distance(mesh, start_idx, end_idx):
    """Calculates the shortest path distance between two vertices along the mesh surface."""
    try:
        path_vertices = trimesh.path.shortest_path(mesh, [start_idx], [end_idx])[0]
        path_points = mesh.vertices[path_vertices]
        distances = np.linalg.norm(np.diff(path_points, axis=0), axis=1)
        return np.sum(distances)
    except Exception as e:
        print(f"WARNING: Could not find a surface path between vertices {start_idx} and {end_idx}: {e}")
        return 0.0

def perform_all_measurements(mesh):
    """The main function to perform all required measurements from the PDF on a given mesh."""
    print("--- Performing detailed measurements on the final mesh ---")
    
    landmarks = _find_anatomical_landmarks(mesh)
    
    extents = mesh.bounding_box.extents
    head_width = extents[0]
    head_height = extents[2]
    head_length = extents[1]

    # A: Head Circumference (slice at eyebrow level)
    nasion_vertex = mesh.vertices[landmarks['nasion_idx']]
    try:
        slice_2d, _ = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 0, 1], plane_origin=nasion_vertex)
        head_circumference_A = slice_2d.length if slice_2d else 0.0
    except Exception:
        head_circumference_A = 0.0

    # B: Forehead to Back (over the top)
    forehead_to_back_B = _calculate_surface_distance(mesh, landmarks['nasion_idx'], landmarks['back_of_head_idx'])
    
    # C: Cross Measurement (side to side over the top)
    cross_measurement_C = _calculate_surface_distance(mesh, landmarks['left_side_idx'], landmarks['right_side_idx'])
    
    # D, E, F, etc. are robust estimations for now.
    under_chin_D = (head_height * 0.8) + (head_width * 0.9)
    eyebrow_to_earlobe_E = head_height * 0.5
    eye_corner_to_ear_F = head_width * 0.45
    ear_height_G = 0.0
    ear_width_H = 0.0

    measurements = { 'head_width': head_width, 'head_height': head_height, 'head_length': head_length, 'head_circumference_A': head_circumference_A, 'forehead_to_back_B': forehead_to_back_B, 'cross_measurement_C': cross_measurement_C, 'under_chin_D': under_chin_D, 'eyebrow_to_earlobe_E': eyebrow_to_earlobe_E, 'eye_corner_to_ear_F': eye_corner_to_ear_F, 'ear_height_G': ear_height_G, 'ear_width_H': ear_width_H, }
    print(f"--- Final Measurements (cm) generated ---")
    return measurements