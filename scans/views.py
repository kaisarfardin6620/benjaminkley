from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
import traceback

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
            results = run_full_scan_pipeline(scan)
            
            measurements = results.get('measurements', {})
            reconstruction = results.get('reconstruction', {})
            
            for key, value in measurements.items():
                if hasattr(scan, key):
                    setattr(scan, key, float(value) / 10.0)
            
            scan.processed_3d_model.name = reconstruction.get('output_model_relative_path')
            scan.status = Scan.Status.COMPLETED

            scan.save()
            response_serializer = ScanDetailSerializer(scan, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            error_message = str(e)
            traceback.print_exc()
            
            scan.status = Scan.Status.FAILED
            scan.failure_reason = error_message
            scan.save()
            
            response_data = {
                "detail": "Scan processing failed.",
                "failure_reason": error_message,
                "scan_id": str(scan.id)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)