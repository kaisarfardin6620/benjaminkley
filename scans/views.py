from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from .models import Scan
from .serializers import ScanCreateSerializer, ScanDetailSerializer
from .utils import process_scan_and_save
from .pagination import ScanListPagination
from .filters import ScanDateFilter
from dashboard.pagination import CustomDashboardPagination
from .pdf_generator import generate_scan_pdf 

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

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        try:
            scan = self.get_object()
        except Scan.DoesNotExist:
            return Response({"error": "Scan not found."}, status=status.HTTP_404_NOT_FOUND)

        # DEBUG: Check if the image field has a file attached
        if scan.image_front:
            print(f"DEBUG: image_front exists. File size: {scan.image_front.size} bytes.")
        else:
            print("DEBUG: image_front does not exist or is not attached to the scan object.")

        pdf_buffer = generate_scan_pdf(scan)

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=f'scan_report_{scan.id}.pdf',
            content_type='application/pdf'
        )
