from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
from .tasks import process_scan_task

class ScanViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users to create, list, and retrieve their scans.
    - POST /api/scans/: Creates a new scan and starts background processing.
    - GET /api/scans/: Lists all of the user's scans for the "My Scan" screen.
    - GET /api/scans/{id}/: Retrieves details for the "My Scan View Details" screen.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensures that users can only see and manage their own scans."""
        return Scan.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Uses a different serializer for creating a scan vs. viewing one."""
        if self.action == 'create':
            return ScanCreateSerializer
        return ScanDetailSerializer

    def perform_create(self, serializer):
        """
        Called after a new Scan is created. This triggers the background AI task.
        """
        scan = serializer.save(user=self.request.user)
        process_scan_task.delay(str(scan.id))