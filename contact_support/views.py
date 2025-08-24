from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import ContactMessageSerializer

class SubmitContactMessageView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        response_data = {
            "message": "Your message has been successfully submitted. Our support team will review it shortly."
        }
        headers = self.get_success_headers(serializer.data)
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)