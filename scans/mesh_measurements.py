import trimesh
import numpy as np
import traceback

def _align_mesh_to_principal_axes(mesh):
    print("--- Aligning mesh to principal axes ---")
    mesh.apply_translation(-mesh.center_mass)
    principal_axes = mesh.principal_inertia_vectors
    
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = principal_axes.T
    
    mesh.apply_transform(np.linalg.inv(transform_matrix))

    if np.mean(mesh.vertices[:, 1]) < 0:
        flip_matrix = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
        mesh.apply_transform(flip_matrix)

    principal_axes = mesh.principal_inertia_vectors
    final_rotation = np.eye(4)
    final_rotation[:3, :3] = principal_axes.T
    mesh.apply_transform(final_rotation)
    
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
    try:
        nose_tip = vertices[landmarks['nose_tip_idx']]
        nasion_est = nose_tip + [0, -extents[1]*0.1, extents[1]*0.15]
        _, _, nasion_idx = trimesh.proximity.closest_point(mesh, [nasion_est])
        landmarks['nasion_idx'] = nasion_idx[0]
    except:
        landmarks['nasion_idx'] = landmarks['nose_tip_idx']
        
    return landmarks

def _calculate_surface_distance(mesh, start_idx, end_idx):
    try:
        path = trimesh.path.shortest_path(mesh, [start_idx], [end_idx])[0]
        if len(path) > 1:
            points = mesh.vertices[path]
            return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))
    except:
        pass
    return float(np.linalg.norm(mesh.vertices[start_idx] - mesh.vertices[end_idx]))

def perform_all_measurements(mesh):
    print("--- Performing detailed measurements ---")
    try:
        mesh = _align_mesh_to_principal_axes(mesh)
        landmarks = _find_anatomical_landmarks(mesh)
        extents = mesh.bounding_box.extents
        
        raw_width = extents[0]
        AVERAGE_HUMAN_HEAD_WIDTH_CM = 15.4
        
        scale_factor = 1.0
        if raw_width > 0:
            scale_factor = AVERAGE_HUMAN_HEAD_WIDTH_CM / raw_width
        
        head_width = extents[0] * scale_factor
        head_length = extents[1] * scale_factor
        head_height = extents[2] * scale_factor

        a, b = head_width / 2, head_length / 2
        head_circumference_A = np.pi * (3*(a+b) - np.sqrt((3*a + b) * (a + 3*b)))

        raw_B = _calculate_surface_distance(mesh, landmarks['nasion_idx'], landmarks['back_of_head_idx'])
        forehead_to_back_B = raw_B * scale_factor
        
        raw_C = _calculate_surface_distance(mesh, landmarks['left_side_idx'], landmarks['right_side_idx'])
        cross_measurement_C = raw_C * scale_factor
        

        under_chin_D = (head_height * 0.8) + (head_width * 0.9)
        eyebrow_to_earlobe_E = head_height * 0.52
        eye_corner_to_ear_F = head_width * 0.48
        
        ear_to_ear = head_width * 0.91 
        eye_to_eye = head_width * 0.24

        ear_height_G = head_height * 0.28

        ear_width_H = ear_height_G * 0.55

        cheek_guard_clearance_L = 2.5 

        cheek_guard_height_M = head_height * 0.35

        cheek_guard_width_N = head_width * 0.92
        
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
        
        measurements = {k: round(float(v), 2) for k, v in measurements.items()}
        return measurements

    except Exception as e:
        print(f"Measurement Error: {e}")
        traceback.print_exc()
        return {}