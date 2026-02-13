from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .serializers import (
    UserSerializer,
    UserRegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer
)


class HealthView(APIView):
    """Endpoint de health check - sem autenticação."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """GET /api/health/"""
        return Response({'status': 'ok'}, status=HTTP_200_OK)


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
            token, created = Token.objects.get_or_create(user=user)
            
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
        
        Response:
        {
            "token": "abc123xyz",
            "user": {...},
            "message": "Login realizado com sucesso"
        }
        """
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
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
        """
        POST /api/auth/logout/
        
        Headers:
        Authorization: Token abc123xyz
        """
        request.user.auth_token.delete()
        return Response({'message': 'Logout realizado com sucesso'}, status=HTTP_200_OK)


class CurrentUserView(APIView):
    """Endpoint para obter dados do usuário autenticado."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/auth/me/
        
        Headers:
        Authorization: Token abc123xyz
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def patch(self, request):
        """
        PATCH /api/auth/me/
        
        Atualizar dados do usuário autenticado
        """
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
        
        Headers:
        Authorization: Token abc123xyz
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
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Regenerar token (opcional, força re-login)
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'Senha alterada com sucesso',
                'token': token.key
            }, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ListUsersView(APIView):
    """Endpoint para listar usuários (apenas admin)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/auth/users/
        
        Listar todos os usuários. Requer autenticação.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Permissão negada. Apenas admin.'},
                status=HTTP_401_UNAUTHORIZED
            )
        
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
