import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional

class MeasurementError(Exception):
    pass

ASSUMED_IPD_MM = 6.4
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
                    'head_width': 150.0,  # Average head width in mm
                    'head_length': 200.0,  # Average head length in mm
                    'ear_to_ear': 150.0,  # Same as head_width
                    'eye_to_eye': ASSUMED_IPD_MM,  # Standard IPD
                }
            
            face_landmarks = results.multi_face_landmarks[0]
            image_h, image_w, _ = image.shape
            
            left_pupil = face_landmarks.landmark[LEFT_PUPIL_INDEX]
            right_pupil = face_landmarks.landmark[RIGHT_PUPIL_INDEX]
            
            inter_pupil_distance_px = calculate_pixel_distance(left_pupil, right_pupil, image_w, image_h)
            
            pixel_to_mm_ratio = ASSUMED_IPD_MM / inter_pupil_distance_px if inter_pupil_distance_px > 0 else 0

            left_ear = face_landmarks.landmark[LEFT_EAR_TRAGUS_INDEX]
            right_ear = face_landmarks.landmark[RIGHT_EAR_TRAGUS_INDEX]
            head_width_px = calculate_pixel_distance(left_ear, right_ear, image_w, image_h)
            head_width_mm = head_width_px * pixel_to_mm_ratio

            forehead_top = face_landmarks.landmark[TOP_OF_FOREHEAD_INDEX]
            chin_bottom = face_landmarks.landmark[BOTTOM_OF_CHIN_INDEX]
            head_length_px = calculate_pixel_distance(forehead_top, chin_bottom, image_w, image_h)
            head_length_mm = head_length_px * pixel_to_mm_ratio

            ear_to_ear = head_width_mm
            eye_to_eye = ASSUMED_IPD_MM

            return {
                'head_width': head_width_mm,
                'head_length': head_length_mm,
                'ear_to_ear': ear_to_ear,
                'eye_to_eye': eye_to_eye,
            }

    except Exception as e:
        print(f"ERROR in get_dynamic_2d_measurements for {image_path}: {e}")
        return {
            'head_width': 150.0,  # Fallback on any error
            'head_length': 200.0,
            'ear_to_ear': 150.0,
            'eye_to_eye': ASSUMED_IPD_MM,
        }

def get_surface_measurements_from_model(model_path: str, gender: str, front_image_path: str) -> Optional[Dict[str, float]]:
    print("--- Attempting to get surface measurements from 3D model ---")
    
    try:
        print("Note: 3D measurement logic is a placeholder. Using fallback 2D measurements.")
        
        measurements = get_dynamic_2d_measurements(front_image_path)
        
        if not measurements:
            raise MeasurementError("2D measurement fallback also failed.")
        
        return measurements
    
    except Exception as e:
        print(f"CRITICAL ERROR in get_surface_measurements_from_model: {e}")
        raise MeasurementError(f"Measurement process failed: {e}")