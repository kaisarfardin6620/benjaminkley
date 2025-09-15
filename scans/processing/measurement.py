import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional
import trimesh

ASSUMED_IPD_CM = 6.4  

LEFT_PUPIL_INDEX = 473
RIGHT_PUPIL_INDEX = 468
LEFT_EAR_TRAGUS_INDEX = 234
RIGHT_EAR_TRAGUS_INDEX = 454
TOP_OF_FOREHEAD_INDEX = 10
BOTTOM_OF_CHIN_INDEX = 152
NOSE_TIP_INDEX = 1
SIDE_PROFILE_EAR_TRAGUS_INDEX = 234 

class MeasurementError(Exception):
    pass

def calculate_pixel_distance(p1, p2, image_width_px: int, image_height_px: int) -> float:
    p1_px = np.array([p1.x * image_width_px, p1.y * image_height_px])
    p2_px = np.array([p2.x * image_width_px, p2.y * image_height_px])
    return np.linalg.norm(p1_px - p2_px)

def get_measurements_from_images(image_paths: Dict[str, str]) -> Dict[str, float]:
    mp_face_mesh = mp.solutions.face_mesh
    
    front_image_path = image_paths.get('front')
    side_image_path = image_paths.get('left')

    if not front_image_path:
        raise MeasurementError("Front image path was not provided.")

    image_front = cv2.imread(front_image_path)
    if image_front is None:
        raise FileNotFoundError(f"Front image not found at: {front_image_path}")

    with mp_face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5) as face_mesh:
        
        results_front = face_mesh.process(cv2.cvtColor(image_front, cv2.COLOR_BGR2RGB))
        
        if not results_front.multi_face_landmarks:
            raise MeasurementError("No face was detected in the front-facing image.")
        
        landmarks_front = results_front.multi_face_landmarks[0]
        h_front, w_front, _ = image_front.shape

        left_pupil = landmarks_front.landmark[LEFT_PUPIL_INDEX]
        right_pupil = landmarks_front.landmark[RIGHT_PUPIL_INDEX]
        ipd_px = calculate_pixel_distance(left_pupil, right_pupil, w_front, h_front)
        
        if ipd_px == 0:
             raise MeasurementError("Could not calculate inter-pupil distance for scaling.")
        pixel_to_cm_ratio = ipd_px / ASSUMED_IPD_CM

        left_ear = landmarks_front.landmark[LEFT_EAR_TRAGUS_INDEX]
        right_ear = landmarks_front.landmark[RIGHT_EAR_TRAGUS_INDEX]
        head_width_px = calculate_pixel_distance(left_ear, right_ear, w_front, h_front)
        head_width_cm = head_width_px / pixel_to_cm_ratio

        forehead_top = landmarks_front.landmark[TOP_OF_FOREHEAD_INDEX]
        chin_bottom = landmarks_front.landmark[BOTTOM_OF_CHIN_INDEX]
        head_height_px = calculate_pixel_distance(forehead_top, chin_bottom, w_front, h_front)
        head_height_cm = head_height_px / pixel_to_cm_ratio

        head_length_cm = head_height_cm * 1.2  
        
        if side_image_path:
            image_side = cv2.imread(side_image_path)
            if image_side is not None:
                results_side = face_mesh.process(cv2.cvtColor(image_side, cv2.COLOR_BGR2RGB))
                if results_side.multi_face_landmarks:
                    landmarks_side = results_side.multi_face_landmarks[0]
                    h_side, w_side, _ = image_side.shape
                    
                    nose_tip = landmarks_side.landmark[NOSE_TIP_INDEX]
                    ear = landmarks_side.landmark[SIDE_PROFILE_EAR_TRAGUS_INDEX]
                    depth_px = abs(nose_tip.x - ear.x) * w_side
                    
                    estimated_depth_cm = (depth_px / pixel_to_cm_ratio) * 2.0 
                    
                    if 15 < estimated_depth_cm < 25:
                        head_length_cm = estimated_depth_cm
                        print(f"INFO: Calculated head depth from side image: {head_length_cm:.2f} cm")
                    else:
                        print(f"WARNING: Side profile depth ({estimated_depth_cm:.2f} cm) is out of range. Using estimate.")
                else:
                    print("WARNING: Could not detect face in side image. Using estimate for head depth.")
            else:
                print(f"WARNING: Side image not found at {side_image_path}. Using estimate for head depth.")
        else:
            print("WARNING: No side image provided. Using estimate for head depth.")
            
        return {
            'head_width': head_width_cm,
            'head_length': head_length_cm,
            'ear_to_ear': head_width_cm,
            'eye_to_eye': ASSUMED_IPD_CM,
            'head_height': head_height_cm,
            'head_circumference_A': (head_width_cm + head_length_cm) * np.pi,
            'forehead_to_back_B': head_length_cm,
            'cross_measurement_C': np.sqrt(head_width_cm**2 + head_length_cm**2),
            'under_chin_D': head_width_cm * 0.7,
            'eyebrow_to_earlobe_E': head_width_cm * 0.6,
            'eye_corner_to_ear_F': head_width_cm * 0.5,
            'ear_height_G': head_height_cm * 0.3,
            'ear_width_H': head_width_cm * 0.2,
            'cheek_guard_clearance_L': head_width_cm * 0.15,
            'cheek_guard_height_M': head_height_cm * 0.25,
            'cheek_guard_width_N': head_width_cm * 0.3,
        }

def get_surface_measurements_from_model(model_path: str, initial_measurements: Dict[str, float]) -> Dict[str, float]:
    print("--- Calculating final measurements from reconstructed mesh ---")
    try:
        mesh = trimesh.load(model_path)
        bounds = mesh.bounds
        
        final_measurements = {
            'head_width': bounds[1][0] - bounds[0][0],
            'head_height': bounds[1][1] - bounds[0][1],
            'head_length': bounds[1][2] - bounds[0][2],
        }

        hull = mesh.convex_hull
        mid_plane_origin = hull.bounds[0] + hull.extents / 2
        section = hull.section(plane_normal=[0, 1, 0], plane_origin=mid_plane_origin)
        
        if section:
            final_measurements['head_circumference_A'] = section.length
        else:
            final_measurements['head_circumference_A'] = (final_measurements['head_width'] + final_measurements['head_length']) * np.pi
        
        combined_measurements = initial_measurements.copy()
        combined_measurements.update(final_measurements)
        combined_measurements['ear_to_ear'] = combined_measurements['head_width']
        
        if any(v <= 0 for v in final_measurements.values()):
            raise MeasurementError("Invalid 3D measurements: negative or zero dimensions")
            
        return combined_measurements

    except Exception as e:
        print(f"ERROR in 3D measurements for {model_path}: {e}. Falling back to initial 2D measurements.")
        return initial_measurements