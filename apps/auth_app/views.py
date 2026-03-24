"""Views de Autenticação."""

import requests
from urllib.parse import quote_plus
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
)
from rest_framework.permissions import AllowAny, IsAuthenticated
import logging
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

from .serializers import (
    UserSerializer,
    UserRegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    AccountSendersResponseSerializer,
    GmailSenderSerializer,
    GmailTemplateSerializer,
    WhatsAppSenderSerializer,
    WhatsAppTemplateSerializer,
)
from .services import AuthService
from .models import (
    GmailSender,
    GmailTemplate,
    WhatsAppSender,
    WhatsAppTemplate,
)
from django.db import transaction


class HealthView(APIView):
    """Endpoint de health check - sem autenticação."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """GET /api/health/"""
        return Response({'status': 'ok'}, status=HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """Endpoint para registro de novo usuário."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/auth/register/
        
        Body:
        {
            "username": "joão",
            "email": "joao@example.com",
            "password": "senha123456",
            "password2": "senha123456",
            "first_name": "João",
            "last_name": "Silva"
        }
        """
        serializer = UserRegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            token = AuthService.get_or_create_token(user)
            
            return Response({
                'message': 'Usuário registrado com sucesso',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=HTTP_201_CREATED)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Endpoint para login do usuário."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        POST /api/auth/login/
        
        Body:
        {
            "username": "joão",
            "password": "senha123456"
        }
        """
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = AuthService.get_or_create_token(user)
            
            return Response({
                'message': 'Login realizado com sucesso',
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Endpoint para logout do usuário."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """POST /api/auth/logout/"""
        AuthService.delete_token(request.user)
        return Response({'message': 'Logout realizado com sucesso'}, status=HTTP_200_OK)


class CurrentUserView(APIView):
    """Endpoint para obter dados do usuário autenticado."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/auth/me/"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def patch(self, request):
        """PATCH /api/auth/me/ - Atualizar dados do usuário"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Endpoint para mudança de senha."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/auth/change-password/
        
        Body:
        {
            "old_password": "senha_antiga",
            "new_password": "nova_senha123",
            "new_password2": "nova_senha123"
        }
        """
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Verificar senha antiga
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Senha atual incorreta.'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Atualizar para nova senha
            new_password = serializer.validated_data['new_password']
            token = AuthService.change_password(user, new_password)
            
            return Response({
                'message': 'Senha alterada com sucesso',
                'token': token.key
            }, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ListUsersView(APIView):
    """Endpoint para listar usuários (apenas admin)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/auth/users/ - Listar usuários (requer admin)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permissão negada. Apenas admin.'},
                status=HTTP_401_UNAUTHORIZED
            )
        
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=HTTP_200_OK)


class AccountSettingsView(APIView):
    """Endpoint para obter/atualizar configurações da conta do usuário autenticado."""
    permission_classes = [IsAuthenticated]

    def _build_response_payload(self, request):
        gmail_senders = GmailSender.objects.filter(user=request.user).prefetch_related('templates').order_by('-created_at')
        whatsapp_senders = WhatsAppSender.objects.filter(user=request.user).prefetch_related('templates').order_by('-created_at')

        return {
            'gmailSenders': gmail_senders,
            'whatsappSenders': whatsapp_senders,
        }

    def _sync_templates(self, sender, templates_data, template_model_cls, template_serializer_cls):
        """Sincroniza templates aninhados de um sender."""
        if templates_data == []:
            template_model_cls.objects.filter(sender=sender).delete()
            return

        if not isinstance(templates_data, list):
            raise ValueError('Formato inválido: templates deve ser um array.')

        existing_templates = template_model_cls.objects.filter(sender=sender)
        existing_by_id = {str(obj.id): obj for obj in existing_templates}
        existing_by_title = {obj.title.strip().lower(): obj for obj in existing_templates if obj.title}
        keep_template_ids = []

        for template_item in templates_data:
            template_item = self._normalize_template_item(template_item, template_model_cls)

            template_id = str(template_item.get('id', '')).strip()
            template_title = str(template_item.get('title', '')).strip()
            normalized_title = template_title.lower() if template_title else ''

            existing_template = None

            if template_id and template_id in existing_by_id:
                existing_template = existing_by_id[template_id]
            elif normalized_title and normalized_title in existing_by_title:
                existing_template = existing_by_title[normalized_title]
            
            # Template existente por ID ou title/name → atualizar
            if existing_template is not None:
                template_serializer = template_serializer_cls(
                    existing_template,
                    data=template_item,
                    partial=True
                )
                template_serializer.is_valid(raise_exception=True)
                updated_template = template_serializer.save()
                keep_template_ids.append(str(updated_template.id))
                existing_by_title[updated_template.title.strip().lower()] = updated_template
            # Novo template (sem ID e sem correspondência por title/name) → criar
            else:
                template_serializer = template_serializer_cls(data=template_item)
                template_serializer.is_valid(raise_exception=True)
                created_template = template_serializer.save(sender=sender)
                keep_template_ids.append(str(created_template.id))
                existing_by_title[created_template.title.strip().lower()] = created_template

        # Deletar templates não mencionados
        if keep_template_ids:
            template_model_cls.objects.filter(sender=sender).exclude(id__in=keep_template_ids).delete()
        else:
            template_model_cls.objects.filter(sender=sender).delete()

    def _normalize_template_item(self, template_item, template_model_cls):
        if isinstance(template_item, str):
            normalized_item = {'title': template_item}
        elif isinstance(template_item, dict):
            normalized_item = dict(template_item)
        else:
            raise ValueError('Formato inválido: cada template deve ser um objeto ou string.')

        if template_model_cls is WhatsAppTemplate:
            template_name = normalized_item.get('name') or normalized_item.get('title')
            normalized_item = {'id': normalized_item.get('id'), 'name': template_name}

        if not normalized_item.get('title') and normalized_item.get('name'):
            normalized_item['title'] = normalized_item.get('name')

        return normalized_item

    def _sync_sender_list(self, request, items, model_cls, serializer_cls, template_model_cls=None, template_serializer_cls=None):
        if items is None:
            return

        if not isinstance(items, list):
            raise ValueError('Formato inválido: esperado array de remetentes.')

        existing = model_cls.objects.filter(user=request.user)
        existing_by_id = {str(obj.id): obj for obj in existing}
        keep_ids = []

        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Formato inválido: cada remetente deve ser um objeto.')

            # Extrair templates do payload antes de passar ao serializer (pois é read-only)
            templates_data = item.pop('templates', None)
            
            sender_id = str(item.get('id', '')).strip()
            if sender_id and sender_id in existing_by_id:
                serializer = serializer_cls(existing_by_id[sender_id], data=item, partial=True)
                serializer.is_valid(raise_exception=True)
                updated = serializer.save()
                keep_ids.append(str(updated.id))
                sender = updated
            else:
                serializer = serializer_cls(data=item)
                serializer.is_valid(raise_exception=True)
                created = serializer.save(user=request.user)
                keep_ids.append(str(created.id))
                sender = created

            # Sincronizar templates aninhados se fornecido
            if template_model_cls and template_serializer_cls and templates_data is not None:
                self._sync_templates(sender, templates_data, template_model_cls, template_serializer_cls)

        if keep_ids:
            model_cls.objects.filter(user=request.user).exclude(id__in=keep_ids).delete()
        else:
            model_cls.objects.filter(user=request.user).delete()

    def get(self, request):
        """GET /api/account/settings/"""
        response_payload = self._build_response_payload(request)

        response_serializer = AccountSendersResponseSerializer(instance=response_payload)
        return Response(response_serializer.data, status=HTTP_200_OK)

    def put(self, request):
        """PUT /api/account/settings/"""
        gmail_senders = request.data.get('gmailSenders')
        whatsapp_senders = request.data.get('whatsappSenders')

        try:
            with transaction.atomic():
                self._sync_sender_list(
                    request,
                    gmail_senders,
                    GmailSender,
                    GmailSenderSerializer,
                    template_model_cls=GmailTemplate,
                    template_serializer_cls=GmailTemplateSerializer
                )
                self._sync_sender_list(
                    request,
                    whatsapp_senders,
                    WhatsAppSender,
                    WhatsAppSenderSerializer,
                    template_model_cls=WhatsAppTemplate,
                    template_serializer_cls=WhatsAppTemplateSerializer
                )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': str(exc)}, status=HTTP_400_BAD_REQUEST)

        response_payload = self._build_response_payload(request)
        response_serializer = AccountSendersResponseSerializer(instance=response_payload)
        return Response(response_serializer.data, status=HTTP_200_OK)

    def patch(self, request):
        """PATCH /api/account/settings/"""
        return self.put(request)


class GmailSenderListCreateView(APIView):
    """CRUD de remetentes Gmail no escopo de conta."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """POST /api/account/gmail/senders/"""
        serializer = GmailSenderSerializer(data=request.data)
        if serializer.is_valid():
            sender = serializer.save(user=request.user)
            return Response(GmailSenderSerializer(sender).data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class GmailSenderDetailView(APIView):
    """Atualizar/deletar remetente Gmail."""
    permission_classes = [IsAuthenticated]

    def _get_sender(self, request, sender_id):
        try:
            return GmailSender.objects.get(id=sender_id, user=request.user)
        except GmailSender.DoesNotExist:
            return None

    def put(self, request, sender_id):
        """PUT /api/account/gmail/senders/<uuid:sender_id>/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente Gmail não encontrado'}, status=404)

        serializer = GmailSenderSerializer(sender, data=request.data, partial=True)
        if serializer.is_valid():
            updated_sender = serializer.save()
            return Response(GmailSenderSerializer(updated_sender).data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, sender_id):
        """DELETE /api/account/gmail/senders/<uuid:sender_id>/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente Gmail não encontrado'}, status=404)
        sender.delete()
        return Response({'message': 'Remetente Gmail removido com sucesso'}, status=HTTP_200_OK)


class GmailTemplateListCreateView(APIView):
    """CRUD de templates Gmail por remetente."""
    permission_classes = [IsAuthenticated]

    def _get_sender(self, request, sender_id):
        try:
            return GmailSender.objects.get(id=sender_id, user=request.user)
        except GmailSender.DoesNotExist:
            return None

    def post(self, request, sender_id):
        """POST /api/account/gmail/senders/<uuid:sender_id>/templates/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente Gmail não encontrado'}, status=404)

        serializer = GmailTemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save(sender=sender)
            return Response(GmailTemplateSerializer(template).data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class GmailTemplateDetailView(APIView):
    """Atualizar/deletar template Gmail por remetente."""
    permission_classes = [IsAuthenticated]

    def _get_template(self, request, sender_id, template_id):
        try:
            sender = GmailSender.objects.get(id=sender_id, user=request.user)
        except GmailSender.DoesNotExist:
            return None

        try:
            return GmailTemplate.objects.get(id=template_id, sender=sender)
        except GmailTemplate.DoesNotExist:
            return None

    def put(self, request, sender_id, template_id):
        """PUT /api/account/gmail/senders/<uuid:sender_id>/templates/<uuid:template_id>/"""
        template = self._get_template(request, sender_id, template_id)
        if not template:
            return Response({'error': 'Template Gmail não encontrado'}, status=404)

        serializer = GmailTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            updated_template = serializer.save()
            return Response(GmailTemplateSerializer(updated_template).data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, sender_id, template_id):
        """DELETE /api/account/gmail/senders/<uuid:sender_id>/templates/<uuid:template_id>/"""
        template = self._get_template(request, sender_id, template_id)
        if not template:
            return Response({'error': 'Template Gmail não encontrado'}, status=404)
        template.delete()
        return Response({'message': 'Template Gmail removido com sucesso'}, status=HTTP_200_OK)


class WhatsAppSenderListCreateView(APIView):
    """CRUD de remetentes WhatsApp no escopo de conta."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """POST /api/account/whatsapp/senders/"""
        serializer = WhatsAppSenderSerializer(data=request.data)
        if serializer.is_valid():
            sender = serializer.save(user=request.user)
            return Response(WhatsAppSenderSerializer(sender).data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class WhatsAppSenderDetailView(APIView):
    """Atualizar/deletar remetente WhatsApp."""
    permission_classes = [IsAuthenticated]

    def _get_sender(self, request, sender_id):
        try:
            return WhatsAppSender.objects.get(id=sender_id, user=request.user)
        except WhatsAppSender.DoesNotExist:
            return None

    def put(self, request, sender_id):
        """PUT /api/account/whatsapp/senders/<uuid:sender_id>/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente WhatsApp não encontrado'}, status=404)

        serializer = WhatsAppSenderSerializer(sender, data=request.data, partial=True)
        if serializer.is_valid():
            updated_sender = serializer.save()
            return Response(WhatsAppSenderSerializer(updated_sender).data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, sender_id):
        """DELETE /api/account/whatsapp/senders/<uuid:sender_id>/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente WhatsApp não encontrado'}, status=404)
        sender.delete()
        return Response({'message': 'Remetente WhatsApp removido com sucesso'}, status=HTTP_200_OK)


class WhatsAppTemplateListCreateView(APIView):
    """CRUD de templates WhatsApp por remetente."""
    permission_classes = [IsAuthenticated]

    def _get_sender(self, request, sender_id):
        try:
            return WhatsAppSender.objects.get(id=sender_id, user=request.user)
        except WhatsAppSender.DoesNotExist:
            return None

    def post(self, request, sender_id):
        """POST /api/account/whatsapp/senders/<uuid:sender_id>/templates/"""
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente WhatsApp não encontrado'}, status=404)

        serializer = WhatsAppTemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save(sender=sender)
            return Response(WhatsAppTemplateSerializer(template).data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class WhatsAppTemplateDetailView(APIView):
    """Atualizar/deletar template WhatsApp por remetente."""
    permission_classes = [IsAuthenticated]

    def _get_template(self, request, sender_id, template_id):
        try:
            sender = WhatsAppSender.objects.get(id=sender_id, user=request.user)
        except WhatsAppSender.DoesNotExist:
            return None

        try:
            return WhatsAppTemplate.objects.get(id=template_id, sender=sender)
        except WhatsAppTemplate.DoesNotExist:
            return None

    def put(self, request, sender_id, template_id):
        """PUT /api/account/whatsapp/senders/<uuid:sender_id>/templates/<uuid:template_id>/"""
        template = self._get_template(request, sender_id, template_id)
        if not template:
            return Response({'error': 'Template WhatsApp não encontrado'}, status=404)

        serializer = WhatsAppTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            updated_template = serializer.save()
            return Response(WhatsAppTemplateSerializer(updated_template).data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, sender_id, template_id):
        """DELETE /api/account/whatsapp/senders/<uuid:sender_id>/templates/<uuid:template_id>/"""
        template = self._get_template(request, sender_id, template_id)
        if not template:
            return Response({'error': 'Template WhatsApp não encontrado'}, status=404)
        template.delete()
        return Response({'message': 'Template WhatsApp removido com sucesso'}, status=HTTP_200_OK)


class WhatsAppTemplatePreviewView(APIView):
    """Busca os detalhes de um template WhatsApp na Graph API para preview e seleção de variáveis."""
    permission_classes = [IsAuthenticated]

    GRAPH_API_VERSION = 'v22.0'
    GRAPH_API_BASE = 'https://graph.facebook.com'

    def _get_sender(self, request, sender_id):
        try:
            return WhatsAppSender.objects.get(id=sender_id, user=request.user)
        except WhatsAppSender.DoesNotExist:
            return None

    def get(self, request, sender_id, template_name):
        """
        GET /api/account/whatsapp/senders/<uuid:sender_id>/templates/<str:template_name>/preview/

        Consulta a Graph API do WhatsApp e retorna os dados do template:
        name, language, status, category e components (HEADER, BODY, FOOTER, BUTTONS).
        """
        sender = self._get_sender(request, sender_id)
        if not sender:
            return Response({'error': 'Remetente WhatsApp não encontrado'}, status=HTTP_404_NOT_FOUND)

        access_token = sender.get_access_token()
        business_id = sender.business_id

        if not access_token:
            return Response({'error': 'Token de acesso não configurado para este remetente'}, status=HTTP_400_BAD_REQUEST)
        if not business_id:
            return Response({'error': 'Business ID não configurado para este remetente'}, status=HTTP_400_BAD_REQUEST)

        encoded_template_name = quote_plus(str(template_name))
        url = f'{self.GRAPH_API_BASE}/{self.GRAPH_API_VERSION}/{business_id}/message_templates?name={encoded_template_name}'
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as exc:
            logger.error(f'[TEMPLATE PREVIEW] Erro de conexão com a Graph API: {exc}')
            return Response({'error': 'Não foi possível conectar à API do WhatsApp'}, status=HTTP_400_BAD_REQUEST)

        if not resp.ok:
            try:
                error_body = resp.json()
            except ValueError:
                error_body = {'raw': resp.text}
            logger.warning(f'[TEMPLATE PREVIEW] Erro da Graph API ({resp.status_code}): {error_body}')
            return Response(
                {'error': 'Erro ao consultar a API do WhatsApp', 'detail': error_body},
                status=resp.status_code,
            )

        data = resp.json().get('data', [])
        if not data:
            return Response({'error': f'Template "{template_name}" não encontrado'}, status=HTTP_404_NOT_FOUND)

        return Response(self._extract_texts(data[0]), status=HTTP_200_OK)

    def _extract_texts(self, template: dict) -> dict:
        """Extrai apenas os textos relevantes de cada componente do template."""
        result = {'name': template.get('name'), 'language': template.get('language')}

        for component in template.get('components', []):
            component_type = (component.get('type') or '').upper()
            if component_type == 'HEADER':
                result['header'] = component.get('text') or ''
            elif component_type == 'BODY':
                result['body'] = component.get('text') or ''
            elif component_type == 'FOOTER':
                result['footer'] = component.get('text') or ''
            elif component_type == 'BUTTONS':
                result['buttons'] = [btn.get('text') for btn in component.get('buttons', []) if btn.get('text')]

        return result
