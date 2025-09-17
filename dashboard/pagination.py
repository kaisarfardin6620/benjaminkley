from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.conf import settings

class CustomDashboardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        incorrect_base = self.request.build_absolute_uri('/')[:-1]
        
        next_link = self.get_next_link()
        previous_link = self.get_previous_link()

        if next_link:
            next_link = next_link.replace(incorrect_base, settings.SERVER_BASE_URL)
        if previous_link:
            previous_link = previous_link.replace(incorrect_base, settings.SERVER_BASE_URL)

        return Response({
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'limit': self.get_page_size(self.request),
                'totalPage': self.page.paginator.num_pages,
            },
            'links': {
                'next': next_link,
                'previous': previous_link,
            },
            'data': data
        })