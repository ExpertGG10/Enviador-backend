"""Permissões customizadas."""

from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Permissão customizada para verificar se o usuário é o proprietário do objeto.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(BasePermission):
    """
    Permissão que permite leitura a qualquer pessoa, mas escrita apenas ao proprietário.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.user == request.user
