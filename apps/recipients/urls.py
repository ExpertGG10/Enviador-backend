"""URLs da app de Destinatários."""

from django.urls import path
from .views import (
    RecipientListCreateView,
    RecipientDetailView,
    RecipientGroupListCreateView,
    RecipientGroupDetailView
)

app_name = 'recipients'

urlpatterns = [
    # Destinatários
    path('', RecipientListCreateView.as_view(), name='list-create'),
    path('<int:pk>/', RecipientDetailView.as_view(), name='detail'),
    
    # Grupos
    path('groups/', RecipientGroupListCreateView.as_view(), name='groups-list-create'),
    path('groups/<int:pk>/', RecipientGroupDetailView.as_view(), name='groups-detail'),
]
