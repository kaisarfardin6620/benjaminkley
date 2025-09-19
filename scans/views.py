from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
from .utils import process_scan_and_save
# from .processing import process_scan_and_save  # Import the new function
from .pagination import ScanListPagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ScanDateFilter
from dashboard.pagination import CustomDashboardPagination

class ScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomDashboardPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = ScanDateFilter

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
            # Replace the Celery task call with a direct, synchronous call
            process_scan_and_save(str(scan.id))
        except Exception as e:
            print(f"Error processing scan for {scan.id}: {e}")
        
        detail_serializer = ScanDetailSerializer(scan, context={'request': request})
        
        response_data = {
            "scan_id": detail_serializer.data.get('scan_id'),
            "status": detail_serializer.data.get('status'),
            "scan_images": detail_serializer.data.get('scan_images'), 
        }

        headers = self.get_success_headers(detail_serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)