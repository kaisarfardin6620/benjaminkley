# scans/processing/gender_predictor.py

from django.conf import settings
import cv2

def predict_gender(image_path: str) -> str:
    """
    Loads the gender detection model and predicts the gender from a given image.
    
    Args:
        image_path: The absolute path to the front-facing user image.

    Returns:
        A string, either 'Male' or 'Female'. Defaults to 'Male' on error.
    """
    try:
        GENDER_MODEL_DIR = settings.AI_MODELS_DIR / 'gender_detection'
        GENDER_PROTO = str(GENDER_MODEL_DIR / 'gender_deploy.prototxt')
        GENDER_MODEL = str(GENDER_MODEL_DIR / 'gender_net.caffemodel')
        
        gender_net = cv2.dnn.readNet(GENDER_MODEL, GENDER_PROTO)
        
        image = cv2.imread(image_path)
        if image is None:
            raise IOError("Image could not be read.")
            
        # The model expects a face image. We assume the input image is already
        # cropped or centered on the face for this function.
        face = image 
        
        MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
        GENDER_LIST = ['Male', 'Female']
        
        blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
        
        gender_net.setInput(blob)
        gender_preds = gender_net.forward()
        return GENDER_LIST[gender_preds[0].argmax()]
        
    except Exception as e:
        print(f"Warning: Gender prediction failed with error: {e}. Defaulting to 'Male'.")
        return 'Male'