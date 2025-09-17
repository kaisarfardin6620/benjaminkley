from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
from .tasks import process_scan_and_save
from dashboard.pagination import CustomDashboardPagination 

class ScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomDashboardPagination 

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
            process_scan_and_save.delay(str(scan.id))
        except Exception as e:
            print(f"Error processing scan {scan.id}: {e}")
        
        detail_serializer = ScanDetailSerializer(scan)
        
        response_data = {
            "scan_id": detail_serializer.data.get('scan_id'),
            "status": detail_serializer.data.get('status'),
            "image_front_url": detail_serializer.data.get('image_front_url'),
            "image_back_url": detail_serializer.data.get('image_back_url'),
            "image_left_url": detail_serializer.data.get('image_left_url'),
            "image_right_url": detail_serializer.data.get('image_right_url'),
        }

        headers = self.get_success_headers(response_data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)