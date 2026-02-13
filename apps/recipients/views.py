"""Views da app de Destinatários."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated

from .models import Recipient, RecipientGroup
from .serializers import (
    RecipientSerializer,
    RecipientGroupSerializer,
    RecipientGroupCreateSerializer
)
from .services import RecipientService, RecipientGroupService


# ============ RECIPIENTS ============

class RecipientListCreateView(APIView):
    """Listar e criar destinatários."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/recipients/ - Listar destinatários."""
        recipients = RecipientService.get_user_recipients(request.user)
        serializer = RecipientSerializer(recipients, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def post(self, request):
        """POST /api/recipients/ - Criar novo destinatário."""
        serializer = RecipientSerializer(data=request.data)
        
        if serializer.is_valid():
            recipient = RecipientService.create_recipient(
                user=request.user,
                email=serializer.validated_data['email'],
                name=serializer.validated_data.get('name', '')
            )[0]
            return Response(
                RecipientSerializer(recipient).data,
                status=HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class RecipientDetailView(APIView):
    """Detalhes, atualização e deleção de destinatário."""
    permission_classes = [IsAuthenticated]
    
    def _get_recipient(self, request, pk):
        """Obter recipient do usuário autenticado."""
        try:
            return Recipient.objects.get(pk=pk, user=request.user)
        except Recipient.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/recipients/{id}/ - Obter detalhes."""
        recipient = self._get_recipient(request, pk)
        if not recipient:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = RecipientSerializer(recipient)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def patch(self, request, pk):
        """PATCH /api/recipients/{id}/ - Atualizar."""
        recipient = self._get_recipient(request, pk)
        if not recipient:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = RecipientSerializer(recipient, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/recipients/{id}/ - Deletar."""
        recipient = self._get_recipient(request, pk)
        if not recipient:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        RecipientService.delete_recipient(recipient)
        return Response({'message': 'Deletado com sucesso'}, status=HTTP_200_OK)


# ============ RECIPIENT GROUPS ============

class RecipientGroupListCreateView(APIView):
    """Listar e criar grupos de destinatários."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/recipient-groups/ - Listar grupos."""
        groups = RecipientGroupService.get_user_groups(request.user)
        serializer = RecipientGroupSerializer(groups, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def post(self, request):
        """POST /api/recipient-groups/ - Criar novo grupo."""
        serializer = RecipientGroupCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            group = RecipientGroupService.create_group(
                user=request.user,
                name=serializer.validated_data['name'],
                recipient_ids=[r.id for r in serializer.validated_data.get('recipient_ids', [])]
            )
            return Response(
                RecipientGroupSerializer(group).data,
                status=HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class RecipientGroupDetailView(APIView):
    """Detalhes, atualização e deleção de grupo."""
    permission_classes = [IsAuthenticated]
    
    def _get_group(self, request, pk):
        """Obter group do usuário autenticado."""
        try:
            return RecipientGroup.objects.get(pk=pk, user=request.user)
        except RecipientGroup.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/recipient-groups/{id}/ - Obter detalhes."""
        group = self._get_group(request, pk)
        if not group:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = RecipientGroupSerializer(group)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def patch(self, request, pk):
        """PATCH /api/recipient-groups/{id}/ - Atualizar."""
        group = self._get_group(request, pk)
        if not group:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = RecipientGroupCreateSerializer(data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_group = RecipientGroupService.update_group(
                group,
                name=serializer.validated_data.get('name'),
                recipient_ids=[r.id for r in serializer.validated_data.get('recipient_ids', [])] or None
            )
            return Response(
                RecipientGroupSerializer(updated_group).data,
                status=HTTP_200_OK
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/recipient-groups/{id}/ - Deletar."""
        group = self._get_group(request, pk)
        if not group:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        RecipientGroupService.delete_group(group)
        return Response({'message': 'Deletado com sucesso'}, status=HTTP_200_OK)
