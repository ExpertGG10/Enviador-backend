"""URLs da app de Emails."""

from django.urls import path
from .views import (
    EmailHistoryListView,
    EmailSendView,
    EmailStatsView
)

app_name = 'emails'

urlpatterns = [
    path('history/', EmailHistoryListView.as_view(), name='history'),
    path('send/', EmailSendView.as_view(), name='send'),
    path('stats/<int:sender_id>/', EmailStatsView.as_view(), name='stats'),
]
