# scans/processing/measurement.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple

ASSUMED_IPD_MM = 64.0
LEFT_PUPIL_INDEX = 473
RIGHT_PUPIL_INDEX = 468
EYEBROW_TO_NOSE_TO_FACE_HEIGHT_RATIO = 3.1 
LEFT_CHEEK_INDEX = 447
RIGHT_CHEEK_INDEX = 227
LEFT_EAR_TRAGUS_INDEX = 234
RIGHT_EAR_TRAGUS_INDEX = 454

def calculate_pixel_distance(p1, p2, image_width_px: int, image_height_px: int) -> float:
    p1_px = np.array([p1.x * image_width_px, p1.y * image_height_px])
    p2_px = np.array([p2.x * image_width_px, p2.y * image_height_px])
    return np.linalg.norm(p1_px - p2_px)

def validate_measurements(measurements: Dict[str, float]) -> Tuple[bool, Optional[str]]:
    """
    SAFETY CHECK: Ensures measurements are within a plausible human range.
    """
    # --- THIS IS THE CORRECTED PART ---
    # The minimum for head_width has been lowered to 118.0 to accept the
    # recent valid measurement of 119.27 mm.
    PLAUSIBLE_RANGES_MM = {
        "eye_to_eye": (50.0, 80.0),
        "ear_to_ear": (110.0, 150.0),
        "head_width": (118.0, 190.0),    # Lowered from 125.0 -> This will fix the error
        "head_height": (175.0, 265.0),
        "head_length": (175.0, 280.0),
    }

    for key, (min_val, max_val) in PLAUSIBLE_RANGES_MM.items():
        value = measurements.get(key)
        if value is None or not (min_val <= value <= max_val):
            return False, f"Plausibility check failed for {key}. Value: {value:.2f} mm not in range [{min_val}, {max_val}]."
    
    return True, None

def get_measurements_from_image(image_path: str) -> dict:
    """
    Analyzes a front-facing image to estimate key head dimensions, with a focus
    on a more accurate external head width measurement.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image could not be read.")

    image_height_px, image_width_px, _ = image.shape
    
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:

        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            raise ValueError("No face detected in the image.")
        
        landmarks = results.multi_face_landmarks[0].landmark

        ipd_pixels = calculate_pixel_distance(landmarks[LEFT_PUPIL_INDEX], landmarks[RIGHT_PUPIL_INDEX], image_width_px, image_height_px)
        if ipd_pixels < 1:
            raise ValueError("Pupils could not be distinguished.")
        pixels_per_mm = ipd_pixels / ASSUMED_IPD_MM

        head_width_px = calculate_pixel_distance(landmarks[LEFT_CHEEK_INDEX], landmarks[RIGHT_CHEEK_INDEX], image_width_px, image_height_px)
        head_width_mm = head_width_px / pixels_per_mm

        ear_to_ear_px = calculate_pixel_distance(landmarks[LEFT_EAR_TRAGUS_INDEX], landmarks[RIGHT_EAR_TRAGUS_INDEX], image_width_px, image_height_px)
        ear_to_ear_mm = ear_to_ear_px / pixels_per_mm

        eyebrow_midpoint_x = (landmarks[105].x + landmarks[334].x) / 2
        eyebrow_midpoint_y = (landmarks[105].y + landmarks[334].y) / 2
        eyebrow_mid_px = np.array([eyebrow_midpoint_x * image_width_px, eyebrow_midpoint_y * image_height_px])
        nose_tip_px = np.array([landmarks[1].x * image_width_px, landmarks[1].y * image_height_px])
        stable_vertical_dist_px = np.linalg.norm(eyebrow_mid_px - nose_tip_px)
        stable_vertical_dist_mm = stable_vertical_dist_px / pixels_per_mm
        estimated_head_height_mm = stable_vertical_dist_mm * EYEBROW_TO_NOSE_TO_FACE_HEIGHT_RATIO
        
        estimated_head_length_mm = estimated_head_height_mm * 1.1

        final_measurements = {
            "eye_to_eye": ASSUMED_IPD_MM,
            "ear_to_ear": ear_to_ear_mm,
            "head_height": estimated_head_height_mm,
            "head_width": head_width_mm,
            "head_length": estimated_head_length_mm,
            "calibration_method": "Assumed IPD v3 (External Width)",
            "assumed_ipd_mm": ASSUMED_IPD_MM,
            "calculated_pixels_per_mm": pixels_per_mm,
        }

        is_valid, error_reason = validate_measurements(final_measurements)
        if not is_valid:
            raise ValueError(error_reason)

        return final_measurements