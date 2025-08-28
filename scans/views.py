# scans/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer

# --- CRITICAL CHANGE: We now import the task, not the pipeline ---
from .tasks import process_scan_task

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
        """
        This is now a fast, asynchronous method.
        It creates the scan, triggers the background task, and responds instantly.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        scan = serializer.instance

        # --- This is the key change ---
        # Instead of running the pipeline, we call .delay() to send it to Celery.
        process_scan_task.delay(str(scan.id))

        headers = self.get_success_headers(serializer.data)
        # We return the initial "PROCESSING" state of the object
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)