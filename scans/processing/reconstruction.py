from django.conf import settings
from pathlib import Path
import trimesh
import tempfile
import os
import numpy as np
from .measurement import get_dynamic_2d_measurements

def reshape_model_to_match_measurements(base_mesh, measurements):
    print("--- Reshaping 3D model based on measurements ---")
    
    bounds = base_mesh.bounds
    current_width = bounds[1][0] - bounds[0][0]  
    current_length = bounds[1][2] - bounds[0][2]  

    target_width = measurements.get('head_width', 15.0)  
    target_length = measurements.get('head_length', 20.0)  

    scale_x = target_width / current_width if current_width > 0 else 1.0
    scale_z = target_length / current_length if current_length > 0 else 1.0
    scale_y = (scale_x + scale_z) / 2  

    base_mesh.apply_scale((scale_x, scale_y, scale_z))
    
    return base_mesh

def generate_head_model_locally(image_paths: dict, scan_id: str, gender: str) -> tuple[str, str]:
    base_heads_dir = Path(settings.AI_MODELS_DIR) / 'base_heads'
    base_model_path = base_heads_dir / ('female_head.obj' if gender == 'Female' else 'male_head.obj')
    
    base_mesh = trimesh.load(str(base_model_path))
    
    # <-- THE FIX IS HERE: We must pass both the front and side image paths -->
    measurements = get_dynamic_2d_measurements(image_paths['front'], image_paths['left'])
    
    if not measurements:
        print("WARNING: No measurements obtained, using default mesh size.")
    
    newly_shaped_mesh = reshape_model_to_match_measurements(base_mesh, measurements)
    
    temp_dir = tempfile.gettempdir()
    output_filename = f"{scan_id}_reconstructed.obj"
    local_temp_path = os.path.join(temp_dir, output_filename)
    
    newly_shaped_mesh.export(local_temp_path)
    
    return local_temp_path, output_filename