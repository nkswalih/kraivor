from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProfileOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        return str(request.user.id) == str(obj.user_id)


class IsAuthenticatedOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated
