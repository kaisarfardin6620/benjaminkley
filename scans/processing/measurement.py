import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple

ASSUMED_IPD_MM = 64.0
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
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5) as face_mesh:

        image = cv2.imread(image_path)
        if image is None: return None
            
        image_height_px, image_width_px, _ = image.shape
        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if not results.multi_face_landmarks: return None
        landmarks = results.multi_face_landmarks[0].landmark

        ipd_pixels = calculate_pixel_distance(landmarks[LEFT_PUPIL_INDEX], landmarks[RIGHT_PUPIL_INDEX], image_width_px, image_height_px)
        if ipd_pixels < 1: return None
        
        pixels_per_mm = ipd_pixels / ASSUMED_IPD_MM

        dynamic_measurements = {
            "eye_to_eye": ASSUMED_IPD_MM,
            "ear_to_ear": calculate_pixel_distance(landmarks[LEFT_EAR_TRAGUS_INDEX], landmarks[RIGHT_EAR_TRAGUS_INDEX], image_width_px, image_height_px) / pixels_per_mm,
            "head_width": calculate_pixel_distance(landmarks[LEFT_CHEEK_INDEX], landmarks[RIGHT_CHEEK_INDEX], image_width_px, image_height_px) / pixels_per_mm,
            "head_height": calculate_pixel_distance(landmarks[TOP_OF_FOREHEAD_INDEX], landmarks[BOTTOM_OF_CHIN_INDEX], image_width_px, image_height_px) / pixels_per_mm,
        }
        return dynamic_measurements

AVERAGE_MALE_MEASUREMENTS_MM = {
    'head_circumference_A': 570.0, 'forehead_to_back_B': 360.0, 'cross_measurement_C': 340.0,
    'under_chin_D': 290.0, 'eyebrow_to_earlobe_E': 95.0, 'eye_corner_to_ear_F': 65.0,
    'ear_height_G': 63.0, 'ear_width_H': 35.0, 'cheek_guard_clearance_L': 75.0,
    'cheek_guard_height_M': 85.0, 'cheek_guard_width_N': 95.0,
}
AVERAGE_FEMALE_MEASUREMENTS_MM = {
    'head_circumference_A': 550.0, 'forehead_to_back_B': 345.0, 'cross_measurement_C': 325.0,
    'under_chin_D': 275.0, 'eyebrow_to_earlobe_E': 90.0, 'eye_corner_to_ear_F': 62.0,
    'ear_height_G': 60.0, 'ear_width_H': 32.0, 'cheek_guard_clearance_L': 72.0,
    'cheek_guard_height_M': 82.0, 'cheek_guard_width_N': 92.0,
}

def get_surface_measurements_from_model(model_path: str, gender: str, front_image_path: str) -> Dict[str, float]:
    print("--- Using SMART BYPASS Measurement Logic ---")

    dynamic_app_measurements = get_dynamic_2d_measurements(front_image_path)
    if dynamic_app_measurements is None:
        raise ValueError("Failed to detect a face or landmarks in the front-facing photo.")

    if gender == "Female":
        static_backend_measurements = AVERAGE_FEMALE_MEASUREMENTS_MM.copy()
    else: 
        static_backend_measurements = AVERAGE_MALE_MEASUREMENTS_MM.copy()

    final_measurements = static_backend_measurements
    final_measurements.update(dynamic_app_measurements)
    
    final_measurements['head_length'] = final_measurements['head_height'] * 1.1

    return {k: round(v, 2) for k, v in final_measurements.items()}