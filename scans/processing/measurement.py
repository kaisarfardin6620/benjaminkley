import cv2
import mediapipe as mp
import numpy as np
from typing import Dict

AVG_IPD_CM = 6.3
HEAD_WIDTH_ADJUSTMENT = 1.10
HEAD_LENGTH_ADJUSTMENT_SIDE_VIEW = 1.15
HEAD_HEIGHT_ADJUSTMENT_SIDE_VIEW = 1.20
ESTIMATED_LENGTH_FROM_WIDTH_RATIO = 1.30
ESTIMATED_HEIGHT_FROM_WIDTH_RATIO = 1.50
ESTIMATED_EAR_HEIGHT_FROM_HEAD_HEIGHT_RATIO = 0.30
EAR_TO_EAR_FROM_WIDTH_RATIO = 1.4
HEAD_CIRCUMFERENCE_FROM_DIMS_ADJUSTMENT = 1.1 
FOREHEAD_TO_BACK_FROM_LENGTH_RATIO = 1.3
UNDER_CHIN_FROM_HEIGHT_RATIO = 1.2
EYEBROW_TO_EARLOBE_FROM_HEIGHT_RATIO = 0.5
EYE_CORNER_TO_EAR_FROM_WIDTH_RATIO = 0.45
EAR_WIDTH_FROM_HEAD_WIDTH_RATIO = 0.25
CHEEK_GUARD_HEIGHT_FROM_HEAD_HEIGHT_RATIO = 0.2
CHEEK_GUARD_WIDTH_FROM_HEAD_WIDTH_RATIO = 0.3
CHEEK_CLEARANCE_FROM_CHEEK_HEIGHT_RATIO = 0.3

class MeasurementError(Exception):
    pass

def get_measurements_from_images(front_image_path: str, side_image_path: str) -> Dict[str, float]:
    print("--- Starting DEFINITIVE 2D measurement process using MediaPipe ---")
    mp_face_mesh = mp.solutions.face_mesh
    
    try:
        front_image = cv2.imread(front_image_path)
        if front_image is None:
            raise MeasurementError("Could not read the front-facing image.")

        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5) as face_mesh:
            results_front = face_mesh.process(cv2.cvtColor(front_image, cv2.COLOR_BGR2RGB))

            if not results_front.multi_face_landmarks:
                raise MeasurementError("Could not detect a face in the front-facing image.")

            landmarks_front = results_front.multi_face_landmarks[0].landmark
            img_h, img_w, _ = front_image.shape

            right_pupil = np.array([landmarks_front[468].x * img_w, landmarks_front[468].y * img_h])
            left_pupil = np.array([landmarks_front[473].x * img_w, landmarks_front[473].y * img_h])
            
            ipd_pixels = np.linalg.norm(left_pupil - right_pupil)
            if ipd_pixels < 10:
                 raise MeasurementError("Face detection in front image is not clear enough to establish a reliable scale.")
            
            CM_PER_PIXEL = AVG_IPD_CM / ipd_pixels
            print(f"Scale established from front image: {CM_PER_PIXEL:.4f} cm/pixel")

            eye_to_eye_cm = ipd_pixels * CM_PER_PIXEL

            head_width_cm = np.linalg.norm(
                np.array([landmarks_front[234].x * img_w, landmarks_front[234].y * img_h]) - 
                np.array([landmarks_front[454].x * img_w, landmarks_front[454].y * img_h])
            ) * CM_PER_PIXEL * HEAD_WIDTH_ADJUSTMENT 

    except Exception as e:
        print(f"FATAL ERROR during FRONT image processing: {e}")
        raise MeasurementError(f"Measurement failed on front image: {e}")

    try:
        side_image = cv2.imread(side_image_path)
        if side_image is None: raise MeasurementError("Could not read side image.")
        side_img_h, side_img_w, _ = side_image.shape

        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.5) as face_mesh:
            results_side = face_mesh.process(cv2.cvtColor(side_image, cv2.COLOR_BGR2RGB))
            if not results_side.multi_face_landmarks:
                raise MeasurementError("Could not detect a face in the side-facing image.")

            landmarks_side = results_side.multi_face_landmarks[0].landmark
            
            nose_tip_x = landmarks_side[1].x * side_img_w
            rear_head_x = min(lm.x for lm in landmarks_side) * side_img_w
            head_length_cm = (nose_tip_x - rear_head_x) * CM_PER_PIXEL * HEAD_LENGTH_ADJUSTMENT_SIDE_VIEW

            top_head_y = min(lm.y for lm in landmarks_side) * side_img_h
            chin_bottom_y = landmarks_side[152].y * side_img_h
            head_height_cm = (chin_bottom_y - top_head_y) * CM_PER_PIXEL * HEAD_HEIGHT_ADJUSTMENT_SIDE_VIEW
            
            ear_top = np.array([landmarks_side[10].y * side_img_h])
            ear_bottom = np.array([landmarks_side[175].y * side_img_h])
            ear_height_G_cm = np.linalg.norm(ear_top - ear_bottom) * CM_PER_PIXEL
            
            print("Side image processed successfully.")

    except Exception as e:
        print(f"WARNING: Could not process side image ({e}). Estimating depth and height from front image measurements.")
        head_length_cm = head_width_cm * ESTIMATED_LENGTH_FROM_WIDTH_RATIO
        head_height_cm = head_width_cm * ESTIMATED_HEIGHT_FROM_WIDTH_RATIO
        ear_height_G_cm = head_height_cm * ESTIMATED_EAR_HEIGHT_FROM_HEAD_HEIGHT_RATIO

    ear_to_ear_cm = head_width_cm * EAR_TO_EAR_FROM_WIDTH_RATIO
    cross_measurement_C_cm = ear_to_ear_cm 
    head_circumference_A_cm = (head_length_cm + head_width_cm) * np.pi / 2 * HEAD_CIRCUMFERENCE_FROM_DIMS_ADJUSTMENT
    forehead_to_back_B_cm = head_length_cm * FOREHEAD_TO_BACK_FROM_LENGTH_RATIO
    under_chin_D_cm = head_height_cm * UNDER_CHIN_FROM_HEIGHT_RATIO
    eyebrow_to_earlobe_E_cm = head_height_cm * EYEBROW_TO_EARLOBE_FROM_HEIGHT_RATIO
    eye_corner_to_ear_F_cm = head_width_cm * EYE_CORNER_TO_EAR_FROM_WIDTH_RATIO
    ear_width_H_cm = head_width_cm * EAR_WIDTH_FROM_HEAD_WIDTH_RATIO
    cheek_guard_height_M_cm = head_height_cm * CHEEK_GUARD_HEIGHT_FROM_HEAD_HEIGHT_RATIO
    cheek_guard_width_N_cm = head_width_cm * CHEEK_GUARD_WIDTH_FROM_HEAD_WIDTH_RATIO
    cheek_guard_clearance_L_cm = cheek_guard_height_M_cm * CHEEK_CLEARANCE_FROM_CHEEK_HEIGHT_RATIO

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