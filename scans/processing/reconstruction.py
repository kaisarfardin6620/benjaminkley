from django.conf import settings
from pathlib import Path
import trimesh
import tempfile
import os

def reshape_model_to_match_measurements(base_mesh, measurements):
    print("--- Reshaping 3D model based on real measurements ---")
    
    bounds = base_mesh.bounds
    center = base_mesh.center_mass
    
    base_mesh.apply_translation(-center)
    
    bounds = base_mesh.bounds
    current_width = bounds[1][0] - bounds[0][0] 
    current_height = bounds[1][1] - bounds[0][1] 
    current_length = bounds[1][2] - bounds[0][2]

    target_width = measurements.get('head_width', 15.0)  
    target_height = measurements.get('head_height', 22.0)
    target_length = measurements.get('head_length', 20.0)

    scale_x = target_width / current_width if current_width > 0 else 1.0
    scale_y = target_height / current_height if current_height > 0 else 1.0
    scale_z = target_length / current_length if current_length > 0 else 1.0
    
    print(f"Applying scaling factors: X={scale_x:.2f}, Y={scale_y:.2f}, Z={scale_z:.2f}")

    base_mesh.apply_scale((scale_x, scale_y, scale_z))
    
    base_mesh.apply_translation(center)
    
    return base_mesh

def generate_head_model_locally(scan_id: str, gender: str, measurements: dict) -> tuple[str, str]:

    base_heads_dir = Path(settings.AI_MODELS_DIR) / 'base_heads'
    base_model_path = base_heads_dir / ('female_head.obj' if gender == 'Female' else 'male_head.obj')
    
    try:
        base_mesh = trimesh.load(str(base_model_path), force='mesh')
    except Exception as e:
        print(f"Error loading base mesh: {e}")
        return None, None

    if not measurements:
        print("WARNING: No measurements provided to shape the model.")
        return None, None
    
    newly_shaped_mesh = reshape_model_to_match_measurements(base_mesh, measurements)
    
    temp_dir = tempfile.gettempdir()
    output_filename = f"{scan_id}_reconstructed.obj"
    local_temp_path = os.path.join(temp_dir, output_filename)
    
    newly_shaped_mesh.export(local_temp_path)
    
    return local_temp_path, output_filename