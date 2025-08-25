# scans/processing/measurement.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple

ASSUMED_IPD_MM = 64.0
LEFT_PUPIL_INDEX = 473
RIGHT_PUPIL_INDEX = 468

def calculate_pixel_distance(p1, p2, image_width_px: int, image_height_px: int) -> float:
    p1_px = np.array([p1.x * image_width_px, p1.y * image_height_px])
    p2_px = np.array([p2.x * image_width_px, p2.y * image_height_px])
    return np.linalg.norm(p1_px - p2_px)

def validate_measurements(measurements: Dict[str, float]) -> Tuple[bool, Optional[str]]:
    """
    SAFETY CHECK: Ensures measurements are within a plausible human range.
    Returns a tuple: (is_valid, error_message).
    """
    PLAUSIBLE_RANGES_MM = {
        "eye_to_eye": (80, 140),
        "ear_to_ear": (120, 180),
        "head_height": (180, 260),
    }

    for key, (min_val, max_val) in PLAUSIBLE_RANGES_MM.items():
        value = measurements.get(key)
        if not (value and min_val <= value <= max_val):
            error_msg = f"Plausibility check failed for {key}. Value: {value:.2f} mm not in range [{min_val}, {max_val}]."
            return False, error_msg
    return True, None

def get_measurements_from_image(image_path: str) -> Optional[Dict[str, float]]:
    """
    Estimates facial measurements from a single front-facing image using
    biometric-based scaling (IPD assumption) and validates them.
    """
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.8) as face_mesh:

        image = cv2.imread(image_path)
        if image is None: raise ValueError(f"Could not read image from path: {image_path}")
            
        image_height_px, image_width_px, _ = image.shape
        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if not results.multi_face_landmarks:
            raise ValueError("Face not detected in the image.")
            
        landmarks = results.multi_face_landmarks[0].landmark

        ipd_pixels = calculate_pixel_distance(
            landmarks[LEFT_PUPIL_INDEX], landmarks[RIGHT_PUPIL_INDEX], image_width_px, image_height_px
        )
        if ipd_pixels < 1: # Avoid division by zero
            raise ValueError("Pupils could not be distinguished.")
        
        pixels_per_mm = ipd_pixels / ASSUMED_IPD_MM

        estimated_measurements = {
            "eye_to_eye": calculate_pixel_distance(landmarks[359], landmarks[130], image_width_px, image_height_px) / pixels_per_mm,
            "ear_to_ear": calculate_pixel_distance(landmarks[454], landmarks[234], image_width_px, image_height_px) / pixels_per_mm,
            "head_height": calculate_pixel_distance(landmarks[10], landmarks[152], image_width_px, image_height_px) / pixels_per_mm,
        }
        estimated_measurements["head_width"] = estimated_measurements["ear_to_ear"]

        is_valid, error_message = validate_measurements(estimated_measurements)
        if not is_valid:
            raise ValueError(error_message)

        estimated_measurements['calibration_method'] = 'Biometric IPD Assumption'
        estimated_measurements['assumed_ipd_mm'] = ASSUMED_IPD_MM
        estimated_measurements['calculated_pixels_per_mm'] = pixels_per_mm

        return estimated_measurements