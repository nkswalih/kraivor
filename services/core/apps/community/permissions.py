from rest_framework.permissions import BasePermission


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return str(request.user_id) == str(obj.author_id)


class IsAuthenticatedOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user_id)
