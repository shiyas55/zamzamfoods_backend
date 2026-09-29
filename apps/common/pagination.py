from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    """
    Standard pagination for the Zamzam Foods platform.
    Defaults to 50 items per page, but supports:
    - ?page_size=N: Custom page size up to max_page_size (2000)
    - ?all=true / ?pagination=false: Disables pagination and returns the complete queryset
    """
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 2000

    def paginate_queryset(self, queryset, request, view=None):
        all_param = request.query_params.get("all", "").lower()
        pagination_param = request.query_params.get("pagination", "").lower()
        page_size_param = request.query_params.get("page_size", "").lower()

        if all_param in ["true", "1"] or pagination_param in ["false", "0"] or page_size_param in ["all", "none"]:
            return None

        return super().paginate_queryset(queryset, request, view)
