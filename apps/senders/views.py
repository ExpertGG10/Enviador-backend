"""Views da app de Remetentes."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Sender, AppPassword
from .serializers import SenderSerializer, SenderCreateSerializer, AppPasswordSerializer, AppPasswordCreateSerializer
from .services import SenderService, AppPasswordService


class SenderListCreateView(APIView):
    """Listar e criar contas remetentes."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/senders/ - Listar contas remetentes do usuário."""
        senders = SenderService.get_user_senders(request.user)
        serializer = SenderSerializer(senders, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def post(self, request):
        """POST /api/senders/ - Criar nova conta remetente."""
        serializer = SenderCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            sender = SenderService.create_sender(
                user=request.user,
                **serializer.validated_data
            )
            return Response(
                SenderSerializer(sender).data,
                status=HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class SenderDetailView(APIView):
    """Detalhes, atualização e deleção de conta remetente."""
    permission_classes = [IsAuthenticated]
    
    def _get_sender(self, request, pk):
        """Obter sender do usuário autenticado."""
        try:
            return Sender.objects.get(pk=pk, user=request.user)
        except Sender.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """GET /api/senders/{id}/ - Obter detalhes da conta."""
        sender = self._get_sender(request, pk)
        if not sender:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = SenderSerializer(sender)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def patch(self, request, pk):
        """PATCH /api/senders/{id}/ - Atualizar conta remetente."""
        sender = self._get_sender(request, pk)
        if not sender:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        serializer = SenderCreateSerializer(data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_sender = SenderService.update_sender(
                sender,
                **serializer.validated_data
            )
            return Response(
                SenderSerializer(updated_sender).data,
                status=HTTP_200_OK
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """DELETE /api/senders/{id}/ - Deletar conta remetente."""
        sender = self._get_sender(request, pk)
        if not sender:
            return Response({'error': 'Não encontrado'}, status=HTTP_404_NOT_FOUND)
        
        SenderService.delete_sender(sender)
        return Response({'message': 'Deletado com sucesso'}, status=HTTP_200_OK)


class SenderDefaultView(APIView):
    """Obter conta remetente padrão."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/senders/default/ - Obter conta padrão."""
        sender = SenderService.get_default_sender(request.user)
        if not sender:
            return Response({'error': 'Nenhuma conta padrão'}, status=HTTP_404_NOT_FOUND)
        
        serializer = SenderSerializer(sender)
        return Response(serializer.data, status=HTTP_200_OK)


# ============ APP PASSWORD VIEWS ============

class AppPasswordSetupView(APIView):
    """Configurar/atualizar senha de aplicativo para um sender."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, sender_id):
        """
        POST /api/senders/{sender_id}/app-password/
        
        Body:
        {
            "app_password": "password123"
        }
        """
        serializer = AppPasswordCreateSerializer(data={'sender_id': sender_id, **request.data})
        
        if serializer.is_valid():
            try:
                sender = Sender.objects.get(id=sender_id, user=request.user)
            except Sender.DoesNotExist:
                return Response(
                    {'error': 'Conta remetente não encontrada'},
                    status=HTTP_404_NOT_FOUND
                )
            
            try:
                app_password = AppPasswordService.set_app_password(
                    sender,
                    serializer.validated_data['app_password']
                )
                return Response(
                    {
                        'message': 'Senha de aplicativo configurada com sucesso',
                        'details': AppPasswordSerializer(app_password).data
                    },
                    status=HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': f'Erro ao configurar senha: {str(e)}'},
                    status=HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class AppPasswordCheckView(APIView):
    """Verificar se um sender tem senha de aplicativo configurada."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, sender_id):
        """GET /api/senders/{sender_id}/app-password/check/"""
        try:
            sender = Sender.objects.get(id=sender_id, user=request.user)
        except Sender.DoesNotExist:
            return Response(
                {'error': 'Conta remetente não encontrada'},
                status=HTTP_404_NOT_FOUND
            )
        
        has_password = AppPasswordService.has_app_password(sender)
        
        return Response({
            'has_app_password': has_password,
            'sender_email': sender.email
        }, status=HTTP_200_OK)


class AppPasswordDeleteView(APIView):
    """Deletar senha de aplicativo."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, sender_id):
        """DELETE /api/senders/{sender_id}/app-password/"""
        try:
            sender = Sender.objects.get(id=sender_id, user=request.user)
        except Sender.DoesNotExist:
            return Response(
                {'error': 'Conta remetente não encontrada'},
                status=HTTP_404_NOT_FOUND
            )
        
        try:
            AppPasswordService.delete_app_password(sender)
            return Response({
                'message': 'Senha de aplicativo deletada com sucesso'
            }, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )
