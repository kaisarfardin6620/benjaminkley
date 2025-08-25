# scans/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
import traceback # Import the traceback module for detailed error logging

from .processing.pipeline import run_full_scan_pipeline

class ScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Scan.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ScanCreateSerializer
        return ScanDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        scan = serializer.instance

        try:
            print(f"Starting SYNCHRONOUS AI pipeline for scan ID: {scan.id}...")
            results = run_full_scan_pipeline(scan)
            
            # --- START OF AGGRESSIVE DEBUGGING ---
            
            print("\n--- DEBUGGING SNAPSHOT ---")
            print(f"Type of 'results': {type(results)}")
            
            measurements = results.get('measurements', {})
            print(f"Type of 'measurements': {type(measurements)}")
            
            # Print the type of every single value we are about to use.
            # This will find the string.
            print(f"Value of eye_to_eye: {measurements.get('eye_to_eye')} (Type: {type(measurements.get('eye_to_eye'))})")
            print(f"Value of ear_to_ear: {measurements.get('ear_to_ear')} (Type: {type(measurements.get('ear_to_ear'))})")
            print(f"Value of head_height: {measurements.get('head_height')} (Type: {type(measurements.get('head_height'))})")
            print(f"Value of head_width: {measurements.get('head_width')} (Type: {type(measurements.get('head_width'))})")
            print(f"Value of head_length: {measurements.get('head_length')} (Type: {type(measurements.get('head_length'))})")
            print("--- END DEBUGGING SNAPSHOT ---\n")

            # --- END OF AGGRESSIVE DEBUGGING ---

            # Now, attempt the conversion
            scan.eye_to_eye = float(measurements.get('eye_to_eye', 0)) / 10.0
            scan.ear_to_ear = float(measurements.get('ear_to_ear', 0)) / 10.0
            scan.head_height = float(measurements.get('head_height', 0)) / 10.0
            scan.head_width = float(measurements.get('head_width', 0)) / 10.0
            scan.head_length = float(measurements.get('head_length', 0)) / 10.0

            scan.calibration_method = measurements.get('calibration_method')
            scan.assumed_ipd_mm = measurements.get('assumed_ipd_mm')
            scan.calculated_pixels_per_mm = measurements.get('calculated_pixels_per_mm')
            
            reconstruction = results.get('reconstruction', {})
            scan.processed_3d_model.name = reconstruction.get('output_model_relative_path')

            scan.status = Scan.Status.COMPLETED
            print(f"SYNCHRONOUS pipeline finished successfully for scan ID: {scan.id}")

            response_serializer = ScanDetailSerializer(scan, context={'request': request})
            response_status = status.HTTP_201_CREATED
            response_data = response_serializer.data

        except Exception as e:
            error_message = str(e)
            # This will now print the full traceback to your console, showing the exact line of the error.
            print(f"CRITICAL ERROR during synchronous processing of scan {scan.id}:")
            traceback.print_exc()
            
            scan.status = Scan.Status.FAILED
            scan.failure_reason = error_message
            
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            response_data = {
                "detail": "Scan processing failed.",
                "failure_reason": error_message,
                "scan_id": scan.id
            }
        
        scan.save()
        return Response(response_data, status=response_status)