"""
Wrapper para WhatsAppAPIService para compatibilidade com views.py
"""

from apps.notifications.services import WhatsAppAPIService

# Alias para compatibilidade
WhatsAppAPI = WhatsAppAPIService
