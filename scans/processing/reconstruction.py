from django.conf import settings
from pathlib import Path
import trimesh
import tempfile
import os

def reshape_model_to_match_measurements(base_mesh, measurements):
    """Stretches or shrinks the base mesh to match target dimensions."""
    print("--- Reshaping 3D model based on measurements ---")
    
    bounds = base_mesh.bounds
    # Calculate current dimensions of the template model
    current_width = bounds[1][0] - bounds[0][0]  # X-axis
    current_height = bounds[1][1] - bounds[0][1] # Y-axis
    current_length = bounds[1][2] - bounds[0][2] # Z-axis (depth)

    # Get target dimensions from the measurement dictionary
    target_width = measurements.get('head_width', 15.0)
    target_height = measurements.get('head_height', 22.0)
    target_length = measurements.get('head_length', 20.0)

    # Calculate scale factors for each axis
    scale_x = target_width / current_width if current_width > 0 else 1.0
    scale_y = target_height / current_height if current_height > 0 else 1.0
    scale_z = target_length / current_length if current_length > 0 else 1.0

    # Apply the transformation
    base_mesh.apply_scale((scale_x, scale_y, scale_z))
    
    return base_mesh

def generate_head_model_locally(scan_id: str, gender: str, measurements: dict) -> tuple[str, str]:
    """
    Generates a reshaped head model based on pre-calculated measurements.
    
    Args:
        scan_id: The UUID of the scan.
        gender: The predicted gender ('Male' or 'Female').
        measurements: A dictionary of head dimensions from get_measurements_from_images().

    Returns:
        A tuple containing the local temp path and the final output filename.
    """
    base_heads_dir = Path(settings.AI_MODELS_DIR) / 'base_heads'
    base_model_path = base_heads_dir / ('female_head.obj' if gender == 'Female' else 'male_head.obj')
    
    if not measurements:
        raise ValueError("Measurements must be provided to generate a head model.")
    
    base_mesh = trimesh.load(str(base_model_path))
    
    # Reshape the model using the provided measurements
    newly_shaped_mesh = reshape_model_to_match_measurements(base_mesh, measurements)
    
    # Save the new model to a temporary local file
    temp_dir = tempfile.gettempdir()
    output_filename = f"{scan_id}_reconstructed.obj"
    local_temp_path = os.path.join(temp_dir, output_filename)
    
    newly_shaped_mesh.export(local_temp_path)
    
    return local_temp_path, output_filename