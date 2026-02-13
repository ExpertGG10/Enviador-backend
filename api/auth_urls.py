from django.urls import path
from . import auth


urlpatterns = [
    # Autenticação
    path('register/', auth.RegisterView.as_view(), name='register'),
    path('login/', auth.LoginView.as_view(), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('me/', auth.CurrentUserView.as_view(), name='current_user'),
    path('change-password/', auth.ChangePasswordView.as_view(), name='change_password'),
    path('users/', auth.ListUsersView.as_view(), name='list_users'),
]
