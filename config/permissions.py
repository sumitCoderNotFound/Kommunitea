"""Reusable DRF permission classes."""
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Read for everyone; create/update/delete only for staff (admin/moderators)."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class ReadOnlyOrCreateForAuthed(permissions.BasePermission):
    """Anyone can read; logged-in users can create; only staff can edit/delete."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "POST":
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_staff)
