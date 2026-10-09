from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 500

    def get_page_size(self, request):
        for param in ('pageSize', 'page_size'):
            if param in request.query_params:
                try:
                    val = int(request.query_params[param])
                    if val > 0:
                        return min(val, self.max_page_size)
                except (ValueError, TypeError):
                    pass
        return super().get_page_size(request)
