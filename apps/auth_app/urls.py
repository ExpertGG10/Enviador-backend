"""URLs da app de Autenticação."""

from django.urls import path
from .views import (
    HealthView,
    RegisterView,
    LoginView,
    LogoutView,
    CurrentUserView,
    ChangePasswordView,
    ListUsersView
)

app_name = 'auth'

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/', ListUsersView.as_view(), name='list-users'),
]
