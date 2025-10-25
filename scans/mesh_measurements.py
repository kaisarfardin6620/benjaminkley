import trimesh
import numpy as np
def _align_mesh_to_principal_axes(mesh):
    print("--- Aligning mesh to principal axes ---")
    
    mesh.apply_translation(-mesh.center_mass)

    principal_axes = mesh.principal_inertia_vectors
    
    extents = mesh.extents
    rotation_matrix = principal_axes.T
    mesh.apply_transform(np.linalg.inv(rotation_matrix))

    if np.mean(mesh.vertices[:, 1]) < 0:
        flip_matrix = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
        mesh.apply_transform(flip_matrix)

    principal_axes = mesh.principal_inertia_vectors
    rotation_matrix = np.eye(4)
    rotation_matrix[:3, :3] = principal_axes.T
    mesh.apply_transform(rotation_matrix)
    
    print("--- Mesh alignment completed. ---")
    return mesh


def _find_anatomical_landmarks(mesh):
    vertices = mesh.vertices
    
    landmarks = {
        'chin_idx': np.argmin(vertices[:, 2]),
        'nose_tip_idx': np.argmax(vertices[:, 1]),
        'top_of_head_idx': np.argmax(vertices[:, 2]),
        'back_of_head_idx': np.argmin(vertices[:, 1]),
        'right_side_idx': np.argmax(vertices[:, 0]),
        'left_side_idx': np.argmin(vertices[:, 0]),
    }
    
    extents = mesh.extents
    head_length_est = extents[1]
    
    nose_tip_vertex = vertices[landmarks['nose_tip_idx']]
    nasion_estimate = nose_tip_vertex + [0, -head_length_est*0.1, head_length_est*0.15]
    _, _, nasion_idx = trimesh.proximity.closest_point(mesh, [nasion_estimate])
    landmarks['nasion_idx'] = nasion_idx[0]
    
    print(f"--- Anatomical landmarks identified ---")
    return landmarks

def _calculate_surface_distance(mesh, start_idx, end_idx):
    try:
        path_vertices = trimesh.path.shortest_path(mesh, [start_idx], [end_idx])[0]
        if len(path_vertices) <= 1:
            return 0.0
        path_points = mesh.vertices[path_vertices]
        distances = np.linalg.norm(np.diff(path_points, axis=0), axis=1)
        return np.sum(distances)
    except Exception as e:
        print(f"WARNING: Could not find a surface path between vertices {start_idx} and {end_idx}: {e}")
        return 0.0

def perform_all_measurements(mesh):
    print("--- Performing detailed measurements on the final mesh ---")
    
    mesh = _align_mesh_to_principal_axes(mesh)
    
    landmarks = _find_anatomical_landmarks(mesh)
    
    extents = mesh.bounding_box.extents
    head_width = extents[0] 
    head_length = extents[1] 
    head_height = extents[2] 

    nasion_vertex = mesh.vertices[landmarks['nasion_idx']]
    try:
        slice_2d, _ = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 0, 1], plane_origin=nasion_vertex)
        head_circumference_A = slice_2d.length if slice_2d else 0.0
    except Exception:
        head_circumference_A = 0.0

    forehead_to_back_B = _calculate_surface_distance(mesh, landmarks['nasion_idx'], landmarks['back_of_head_idx'])
    
    cross_measurement_C = _calculate_surface_distance(mesh, landmarks['left_side_idx'], landmarks['right_side_idx'])
    
    under_chin_D = (head_height * 0.8) + (head_width * 0.9)
    eyebrow_to_earlobe_E = head_height * 0.5
    eye_corner_to_ear_F = head_width * 0.45
    
    ear_to_ear = head_width * 0.8 
    eye_to_eye = head_width * 0.2 
    ear_height_G = 0.0
    ear_width_H = 0.0
    cheek_guard_clearance_L = 0.0
    cheek_guard_height_M = 0.0
    cheek_guard_width_N = 0.0

    measurements = { 
        'head_width': head_width, 
        'head_height': head_height, 
        'head_length': head_length,
        'ear_to_ear': ear_to_ear,
        'eye_to_eye': eye_to_eye,
        'head_circumference_A': head_circumference_A, 
        'forehead_to_back_B': forehead_to_back_B, 
        'cross_measurement_C': cross_measurement_C, 
        'under_chin_D': under_chin_D, 
        'eyebrow_to_earlobe_E': eyebrow_to_earlobe_E, 
        'eye_corner_to_ear_F': eye_corner_to_ear_F, 
        'ear_height_G': ear_height_G, 
        'ear_width_H': ear_width_H,
        'cheek_guard_clearance_L': cheek_guard_clearance_L,
        'cheek_guard_height_M': cheek_guard_height_M,
        'cheek_guard_width_N': cheek_guard_width_N,
    }
    
    scale_factor = 1.0 
                       
    measurements = {k: v * scale_factor for k, v in measurements.items()}
    
    print(f"--- Final Measurements (cm) generated ---")
    return measurements