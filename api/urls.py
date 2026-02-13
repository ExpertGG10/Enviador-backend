from django.urls import path, include
from . import views


urlpatterns = [
    # Health check
    path('health/', views.health_view, name='health'),
    
    # Envio de mensagens (requer autenticação)
    # Rotas específicas por canal
    path('send-email/', views.send_email_view, name='send_email'),
    path('send-whatsapp/', views.send_whatsapp_view, name='send_whatsapp'),
    # Rota genérica (deprecated, mas mantida para retrocompatibilidade)
    path('send/', views.send_view, name='send'),
    # Job endpoints for background sending (polling)
    path('jobs/start/', views.jobs_start_view, name='jobs_start'),
    path('jobs/<str:job_id>/', views.jobs_status_view, name='jobs_status'),
    path('jobs/<str:job_id>/cancel/', views.jobs_cancel_view, name='jobs_cancel'),
    
    # WhatsApp (requer autenticação)
    path('whatsapp/test/', views.whatsapp_test_view, name='whatsapp_test'),
    path('whatsapp/webhook/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
    path('whatsapp/webhook/verify/', views.whatsapp_webhook_verify_view, name='whatsapp_webhook_verify'),
    path('whatsapp/setup/', views.whatsapp_setup_view, name='whatsapp_setup'),
]
