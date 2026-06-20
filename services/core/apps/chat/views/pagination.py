from rest_framework.pagination import CursorPagination


class MessageCursorPagination(CursorPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    ordering = '-created_at'
