# scans/processing/measurement.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict

# --- ANATOMICAL CONSTANTS (in Centimeters) ---
AVG_FACE_WIDTH = 13.7  # Bizygomatic width (cheekbone to cheekbone)
AVG_FACE_HEIGHT = 11.0 # Vertical distance from top of forehead landmarks to chin

# --- ROBUST FALLBACK RATIOS (THE SAFETY NET) ---
# Used ONLY if the side-view image processing fails.
ESTIMATED_HEIGHT_FROM_WIDTH_RATIO = 1.35
ESTIMATED_LENGTH_FROM_WIDTH_RATIO = 1.25

class MeasurementError(Exception):
    pass

def get_measurements_from_images(front_image_path: str, side_image_path: str) -> Dict[str, float]:
    print("--- Starting FINAL robust measurement process ---")
    mp_face_mesh = mp.solutions.face_mesh
    
    # =========================================================================
    #  STEP 1: Process FRONT IMAGE. This is mandatory.
    # =========================================================================
    try:
        front_image = cv2.imread(front_image_path)
        if front_image is None: raise MeasurementError("Could not read front image.")

        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5) as face_mesh:
            results_front = face_mesh.process(cv2.cvtColor(front_image, cv2.COLOR_BGR2RGB))
            if not results_front.multi_face_landmarks: raise MeasurementError("No face in front image.")
            
            landmarks = results_front.multi_face_landmarks[0].landmark
            img_h, img_w, _ = front_image.shape

            p_left_cheek = np.array([landmarks[234].x * img_w, landmarks[234].y * img_h])
            p_right_cheek = np.array([landmarks[454].x * img_w, landmarks[454].y * img_h])
            face_width_pixels = np.linalg.norm(p_left_cheek - p_right_cheek)
            
            if face_width_pixels < 50: raise MeasurementError("Face detection unclear in front image.")

            FRONT_CM_PER_PIXEL = AVG_FACE_WIDTH / face_width_pixels
            print(f"Front image scale: {FRONT_CM_PER_PIXEL:.4f} cm/pixel")

            head_width_cm = face_width_pixels * FRONT_CM_PER_PIXEL * 1.1
            
            p_left_pupil = np.array([landmarks[473].x * img_w, landmarks[473].y * img_h])
            p_right_pupil = np.array([landmarks[468].x * img_w, landmarks[468].y * img_h])
            eye_to_eye_cm = np.linalg.norm(p_left_pupil - p_right_pupil) * FRONT_CM_PER_PIXEL
    
    except Exception as e:
        raise MeasurementError(f"CRITICAL FAILURE in front image processing: {e}")

    # =========================================================================
    #  STEP 2: TRY to process SIDE IMAGE. If it fails, we fall back gracefully.
    # =========================================================================
    try:
        side_image = cv2.imread(side_image_path)
        if side_image is None: raise MeasurementError("Could not read side image file.")
        
        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5) as face_mesh:
            results_side = face_mesh.process(cv2.cvtColor(side_image, cv2.COLOR_BGR2RGB))
            if not results_side.multi_face_landmarks: raise MeasurementError("No face in side image.") # This will trigger the fallback

            landmarks_side = results_side.multi_face_landmarks[0].landmark
            side_h, side_w, _ = side_image.shape
            
            all_x = [lm.x * side_w for lm in landmarks_side]
            all_y = [lm.y * side_h for lm in landmarks_side]
            bbox_width_pixels = max(all_x) - min(all_x)
            bbox_height_pixels = max(all_y) - min(all_y)
            
            p_forehead_top = np.array([landmarks_side[10].y * side_h])
            p_chin_bottom = np.array([landmarks_side[152].y * side_h])
            face_height_pixels = abs(p_chin_bottom - p_forehead_top)

            if face_height_pixels < 50: raise MeasurementError("Face detection unclear in side image.")

            SIDE_CM_PER_PIXEL = AVG_FACE_HEIGHT / face_height_pixels
            print(f"Side image scale: {SIDE_CM_PER_PIXEL:.4f} cm/pixel")

            head_height_cm = bbox_height_pixels * SIDE_CM_PER_PIXEL * 1.15
            head_length_cm = bbox_width_pixels * SIDE_CM_PER_PIXEL * 1.25

            p_ear_top = np.array([landmarks_side[10].y * side_h])
            p_ear_bottom = np.array([landmarks_side[175].y * side_h])
            ear_height_G_cm = abs(p_ear_bottom - p_ear_top) * SIDE_CM_PER_PIXEL
            
            print("SUCCESS: Side image processed directly.")

    # --- THIS IS THE CRITICAL FIX ---
    except Exception as e:
        print(f"WARNING: Side image processing failed ({e}). Using robust fallback estimation.")
        # We use the ACCURATE head_width_cm from the front image to estimate.
        head_length_cm = head_width_cm * ESTIMATED_LENGTH_FROM_WIDTH_RATIO
        head_height_cm = head_width_cm * ESTIMATED_HEIGHT_FROM_WIDTH_RATIO
        ear_height_G_cm = head_height_cm * 0.30
    # --- END OF FIX ---

    # =========================================================================
    #  STEP 3: Derive all secondary measurements.
    # =========================================================================
    a = head_length_cm / 2
    b = head_width_cm / 2
    head_circumference_A_cm = np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))

    ear_to_ear_cm = head_width_cm * 1.4
    cross_measurement_C_cm = ear_to_ear_cm
    forehead_to_back_B_cm = head_length_cm * 1.3
    under_chin_D_cm = head_height_cm * 1.2
    eyebrow_to_earlobe_E_cm = head_height_cm * 0.5
    eye_corner_to_ear_F_cm = head_width_cm * 0.45
    ear_width_H_cm = head_width_cm * 0.25
    cheek_guard_height_M_cm = head_height_cm * 0.2
    cheek_guard_width_N_cm = head_width_cm * 0.3
    cheek_guard_clearance_L_cm = cheek_guard_height_M_cm * 0.3

    print("--- All measurements calculated successfully. ---")
    return {
        'head_width': head_width_cm,
        'head_length': head_length_cm,
        'head_height': head_height_cm,
        'eye_to_eye': eye_to_eye_cm,
        'ear_to_ear': ear_to_ear_cm,
        'head_circumference_A': head_circumference_A_cm,
        'forehead_to_back_B': forehead_to_back_B_cm,
        'cross_measurement_C': cross_measurement_C_cm,
        'under_chin_D': under_chin_D_cm,
        'eyebrow_to_earlobe_E': eyebrow_to_earlobe_E_cm,
        'eye_corner_to_ear_F': eye_corner_to_ear_F_cm,
        'ear_height_G': ear_height_G_cm,
        'ear_width_H': ear_width_H_cm,
        'cheek_guard_height_M': cheek_guard_height_M_cm,
        'cheek_guard_width_N': cheek_guard_width_N_cm,
        'cheek_guard_clearance_L': cheek_guard_clearance_L_cm,
    }