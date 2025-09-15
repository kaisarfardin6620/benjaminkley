import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional
import trimesh
from trimesh import proximity, curvature

class MeasurementError(Exception):
    pass

ASSUMED_IPD_CM = 6.4  
LEFT_PUPIL_INDEX = 473
RIGHT_PUPIL_INDEX = 468
LEFT_CHEEK_INDEX = 447
RIGHT_CHEEK_INDEX = 227
LEFT_EAR_TRAGUS_INDEX = 234
RIGHT_EAR_TRAGUS_INDEX = 454
TOP_OF_FOREHEAD_INDEX = 10
BOTTOM_OF_CHIN_INDEX = 152

def calculate_pixel_distance(p1, p2, image_width_px: int, image_height_px: int) -> float:
    p1_px = np.array([p1.x * image_width_px, p1.y * image_height_px])
    p2_px = np.array([p2.x * image_width_px, p2.y * image_height_px])
    return np.linalg.norm(p1_px - p2_px)

def get_dynamic_2d_measurements(image_path: str) -> Optional[Dict[str, float]]:
    try:
        mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(
                static_image_mode=True, max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=0.5) as face_mesh:
            
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError(f"Image not found at path: {image_path}")
            
            results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            if not results.multi_face_landmarks:
                print(f"WARNING: No face landmarks detected in image: {image_path}. Using default measurements.")
                return {
                    'head_width': 15.0,
                    'head_length': 20.0,
                    'ear_to_ear': 15.0,
                    'eye_to_eye': ASSUMED_IPD_CM,
                    'head_height': 20.0,
                    'head_circumference_A': 55.0,  
                    'forehead_to_back_B': 20.0,  
                    'cross_measurement_C': 15.0,  
                    'under_chin_D': 10.0,  
                    'eyebrow_to_earlobe_E': 8.0, 
                    'eye_corner_to_ear_F': 7.0, 
                    'ear_height_G': 6.5,  
                    'ear_width_H': 3.5, 
                    'cheek_guard_clearance_L': 2.0,  
                    'cheek_guard_height_M': 5.0,  
                    'cheek_guard_width_N': 4.0, 
                }
            
            face_landmarks = results.multi_face_landmarks[0]
            image_h, image_w, _ = image.shape
            
            left_pupil = face_landmarks.landmark[LEFT_PUPIL_INDEX]
            right_pupil = face_landmarks.landmark[RIGHT_PUPIL_INDEX]
            inter_pupil_distance_px = calculate_pixel_distance(left_pupil, right_pupil, image_w, image_h)
            pixel_to_cm_ratio = ASSUMED_IPD_CM / inter_pupil_distance_px if inter_pupil_distance_px > 0 else 0

            left_ear = face_landmarks.landmark[LEFT_EAR_TRAGUS_INDEX]
            right_ear = face_landmarks.landmark[RIGHT_EAR_TRAGUS_INDEX]
            head_width_px = calculate_pixel_distance(left_ear, right_ear, image_w, image_h)
            head_width_cm = head_width_px * pixel_to_cm_ratio

            forehead_top = face_landmarks.landmark[TOP_OF_FOREHEAD_INDEX]
            chin_bottom = face_landmarks.landmark[BOTTOM_OF_CHIN_INDEX]
            head_length_px = calculate_pixel_distance(forehead_top, chin_bottom, image_w, image_h)
            head_length_cm = head_length_px * pixel_to_cm_ratio

            left_cheek = face_landmarks.landmark[LEFT_CHEEK_INDEX]
            right_cheek = face_landmarks.landmark[RIGHT_CHEEK_INDEX]
            cheek_width_px = calculate_pixel_distance(left_cheek, right_cheek, image_w, image_h)
            cheek_width_cm = cheek_width_px * pixel_to_cm_ratio

            return {
                'head_width': head_width_cm,
                'head_length': head_length_cm,
                'ear_to_ear': head_width_cm,
                'eye_to_eye': ASSUMED_IPD_CM,
                'head_height': head_length_cm,  
                'head_circumference_A': head_width_cm * 3.14,  
                'forehead_to_back_B': head_length_cm,
                'cross_measurement_C': head_width_cm,
                'under_chin_D': cheek_width_cm * 0.8,  
                'eyebrow_to_earlobe_E': head_width_cm * 0.6,  
                'eye_corner_to_ear_F': head_width_cm * 0.5,  
                'ear_height_G': head_length_cm * 0.3,  
                'ear_width_H': head_width_cm * 0.25, 
                'cheek_guard_clearance_L': cheek_width_cm * 0.2, 
                'cheek_guard_height_M': head_length_cm * 0.25,  
                'cheek_guard_width_N': cheek_width_cm * 0.3, 
            }

    except Exception as e:
        print(f"ERROR in get_dynamic_2d_measurements for {image_path}: {e}")
        return {
            'head_width': 15.0,
            'head_length': 20.0,
            'ear_to_ear': 15.0,
            'eye_to_eye': ASSUMED_IPD_CM,
            'head_height': 20.0,
            'head_circumference_A': 55.0,
            'forehead_to_back_B': 20.0,
            'cross_measurement_C': 15.0,
            'under_chin_D': 10.0,
            'eyebrow_to_earlobe_E': 8.0,
            'eye_corner_to_ear_F': 7.0,
            'ear_height_G': 6.5,
            'ear_width_H': 3.5,
            'cheek_guard_clearance_L': 2.0,
            'cheek_guard_height_M': 5.0,
            'cheek_guard_width_N': 4.0,
        }

def get_surface_measurements_from_model(model_path: str, gender: str, front_image_path: str) -> Optional[Dict[str, float]]:
    print("--- Calculating 3D measurements from reconstructed mesh ---")
    
    try:
        mesh = trimesh.load(model_path)
        
        bounds = mesh.bounds
        head_width_cm = bounds[1][0] - bounds[0][0]  
        head_length_cm = bounds[1][2] - bounds[0][2]  
        head_height_cm = bounds[1][1] - bounds[0][1]  

        hull = mesh.convex_hull
        mid_plane = (bounds[1][1] + bounds[0][1]) / 2
        section = hull.section(plane_normal=[0, 1, 0], plane_origin=[0, mid_plane, 0])
        if section:
            circumference_cm = section.length / 10.0  
        else:
            circumference_cm = head_width_cm * 3.14 

        vertices = mesh.vertices
        x_coords = vertices[:, 0]
        y_coords = vertices[:, 1]
        z_coords = vertices[:, 2]

        ear_height_cm = head_height_cm * 0.3  
        ear_width_cm = head_width_cm * 0.25 

        cheek_guard_height_cm = head_height_cm * 0.25
        cheek_guard_width_cm = head_width_cm * 0.3
        cheek_guard_clearance_cm = head_width_cm * 0.2

        measurements_2d = get_dynamic_2d_measurements(front_image_path)
        eye_to_eye_cm = measurements_2d.get('eye_to_eye', ASSUMED_IPD_CM)
        eyebrow_to_earlobe_cm = measurements_2d.get('eyebrow_to_earlobe_E', head_width_cm * 0.6)
        eye_corner_to_ear_cm = measurements_2d.get('eye_corner_to_ear_F', head_width_cm * 0.5)

        measurements = {
            'head_width': head_width_cm,
            'head_length': head_length_cm,
            'ear_to_ear': head_width_cm,
            'eye_to_eye': eye_to_eye_cm,
            'head_height': head_height_cm,
            'head_circumference_A': circumference_cm,
            'forehead_to_back_B': head_length_cm,
            'cross_measurement_C': head_width_cm,  
            'under_chin_D': head_width_cm * 0.8,  
            'eyebrow_to_earlobe_E': eyebrow_to_earlobe_cm,
            'eye_corner_to_ear_F': eye_corner_to_ear_cm,
            'ear_height_G': ear_height_cm,
            'ear_width_H': ear_width_cm,
            'cheek_guard_clearance_L': cheek_guard_clearance_cm,
            'cheek_guard_height_M': cheek_guard_height_cm,
            'cheek_guard_width_N': cheek_guard_width_cm,
        }
        
        if any(v <= 0 for v in [head_width_cm, head_length_cm, head_height_cm, circumference_cm]):
            raise MeasurementError("Invalid 3D measurements: negative or zero dimensions")
        
        return measurements
    
    except Exception as e:
        print(f"ERROR in 3D measurements for {model_path}: {e}. Falling back to 2D measurements.")
        measurements = get_dynamic_2d_measurements(front_image_path)
        
        if not measurements:
            raise MeasurementError("Both 3D and 2D measurement calculations failed.")
        
        return measurements