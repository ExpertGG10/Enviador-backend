"""URLs da app de Remetentes."""

from django.urls import path
from .views import (
    SenderListCreateView,
    SenderDetailView,
    SenderDefaultView,
    AppPasswordSetupView,
    AppPasswordCheckView,
    AppPasswordDeleteView
)

app_name = 'senders'

urlpatterns = [
    path('', SenderListCreateView.as_view(), name='list-create'),
    path('<int:pk>/', SenderDetailView.as_view(), name='detail'),
    path('default/', SenderDefaultView.as_view(), name='default'),
    
    # App Password Management
    path('<int:sender_id>/app-password/', AppPasswordSetupView.as_view(), name='app-password-setup'),
    path('<int:sender_id>/app-password/check/', AppPasswordCheckView.as_view(), name='app-password-check'),
    path('<int:sender_id>/app-password/', AppPasswordDeleteView.as_view(), name='app-password-delete'),
]
