import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .whatsapp_api import WhatsAppAPI
from .webhook_handler import log_webhook_event, parse_webhook_event
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
import threading

# job manager for background runs
from .services import job_manager


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def health_view(request):
    return JsonResponse({"status": "ok"})


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_email_view(request):
    """
    Endpoint para enviar emails.
    
    POST /api/send-email/
    
    {
        "email_sender": "seu.email@gmail.com",
        "app_password": "sua_senha_de_app",
        "subject": "Assunto do email",
        "message": "<html>Corpo do email</html>",
        "rows": [
            {"email": "destino1@example.com", "file": "caminho_arquivo_1"},
            {"email": "destino2@example.com", "file": "caminho_arquivo_2"}
        ],
        "contact_column": "email",
        "file_column": "file",
        "attach_to_all": false
    }
    """
    user = request.user
    
    # Parse payload from JSON or multipart form data
    if request.content_type and request.content_type.startswith('multipart/'):
        payload_raw = request.POST.get('payload')
        if not payload_raw:
            return HttpResponseBadRequest('Missing payload in multipart form')
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON in payload field')
        
        files_bytes = {}
        for key in request.FILES:
            file_list = request.FILES.getlist(key)
            files_bytes[key] = []
            for f in file_list:
                f.seek(0)
                content = f.read()
                files_bytes[key].append({
                    'name': f.name,
                    'content': content,
                    'size': len(content)
                })
        
        attachment_names = [f.name for f in request.FILES.getlist(list(request.FILES.keys())[0]) if request.FILES]
        payload['attachment_names'] = attachment_names
        payload['_files'] = files_bytes
    else:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON')

    # Validate email-specific required fields
    email_sender_requested = payload.get('email_sender')
    app_password = payload.get('app_password')
    subject = payload.get('subject', '')
    message = payload.get('message', '')
    rows = payload.get('rows', [])
    contact_column = payload.get('contact_column', '')
    
    # Usar o email do usuário autenticado, não o valor do payload
    email_sender = request.user.email
    
    if not email_sender:
        return JsonResponse({"error": "email_sender is required"}, status=400)
    if not app_password:
        return JsonResponse({"error": "app_password is required"}, status=400)
    if not subject:
        return JsonResponse({"error": "subject is required"}, status=400)
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)
    if not contact_column:
        return JsonResponse({"error": "contact_column is required"}, status=400)
    if not rows:
        return JsonResponse({"error": "rows is required"}, status=400)
    
    
    # Call email service
    try:
        from .services.email_service import EmailService
        response = EmailService.send(payload)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return JsonResponse({
            "error": f"Erro ao processar envio: {str(e)}",
            "status": "error"
        }, status=500)
    
    return JsonResponse(response, status=202)


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_whatsapp_view(request):
    """
    Endpoint para enviar mensagens WhatsApp.
    
    POST /api/send-whatsapp/
    
    {
        "phone_number": "5541997393566",
        "message": "Sua mensagem aqui",
        "rows": [
            {"telefone": "5541999999999"},
            {"telefone": "5541888888888"}
        ],
        "contact_column": "telefone",
        "file_column": null,
        "attach_to_all": false
    }
    """
    origin = request.META.get('HTTP_ORIGIN', 'NO_ORIGIN')
    user = request.user
    print(f"\n{'='*80}")
    print(f"[BACKEND WHATSAPP] Requisição recebida de: {origin}")
    print(f"[BACKEND WHATSAPP] Usuário autenticado: {user.username}")
    print(f"[BACKEND WHATSAPP] Content-Type: {request.content_type}")
    
    # Parse payload from JSON or multipart form data
    if request.content_type and request.content_type.startswith('multipart/'):
        payload_raw = request.POST.get('payload')
        if not payload_raw:
            return HttpResponseBadRequest('Missing payload in multipart form')
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON in payload field')
        
        files_bytes = {}
        for key in request.FILES:
            file_list = request.FILES.getlist(key)
            files_bytes[key] = []
            for f in file_list:
                f.seek(0)
                content = f.read()
                files_bytes[key].append({
                    'name': f.name,
                    'content': content,
                    'size': len(content)
                })
        
        payload['_files'] = files_bytes
    else:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON')

    # Validate WhatsApp-specific required fields
    phone_number = payload.get('phone_number')
    message = payload.get('message', '')
    rows = payload.get('rows', [])
    contact_column = payload.get('contact_column', '')
    
    if not phone_number:
        return JsonResponse({"error": "phone_number is required"}, status=400)
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)
    if not contact_column:
        return JsonResponse({"error": "contact_column is required"}, status=400)
    if not rows:
        return JsonResponse({"error": "rows is required"}, status=400)
    
    # Call WhatsApp service
    try:
        from .services.whatsapp_service import WhatsAppService
        response = WhatsAppService.send(payload)
    except Exception as e:
        return JsonResponse({
            "error": f"Erro ao processar envio: {str(e)}",
            "status": "error"
        }, status=500)
    
    return JsonResponse(response, status=202)


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_view(request):
    """
    Endpoint genérico para enviar emails ou mensagens WhatsApp (DEPRECATED - usar send-email ou send-whatsapp)
    
    POST /api/send/
    
    {
        "channel": "email" ou "whatsapp",
        ...
    }
    """
    origin = request.META.get('HTTP_ORIGIN', 'NO_ORIGIN')
    user = request.user
    print(f"\n{'='*80}")
    print(f"[BACKEND GENERIC] Requisição recebida de: {origin}")
    print(f"[BACKEND GENERIC] Usuário autenticado: {user.username}")
    print(f"[BACKEND GENERIC] Content-Type: {request.content_type}")
    
    # Accept JSON or multipart/form-data (with files). If multipart, payload must be in a 'payload' form field as JSON
    if request.content_type and request.content_type.startswith('multipart/'):
        payload_raw = request.POST.get('payload')
        if not payload_raw:
            return HttpResponseBadRequest('Missing payload in multipart form')
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON in payload field')
        # Collect all uploaded files (support multiple keys / multiple files)
        files = []
        for key in request.FILES:
            file_list = request.FILES.getlist(key)
            files.extend(file_list)
        attachment_names = [f.name for f in files]
        print(f"[BACKEND] Arquivos recebidos: {attachment_names}")
        payload['attachment_names'] = attachment_names
        payload['_files'] = request.FILES  # pass files for services if needed
    else:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON')

    print(f"[BACKEND] Payload recebido:")
    print(f"  - Canal: {payload.get('channel')}")
    print(f"  - Assunto: {payload.get('subject', 'N/A')}")
    print(f"  - Mensagem: {payload.get('message')[:50]}..." if len(payload.get('message', '')) > 50 else f"  - Mensagem: {payload.get('message')}")
    print(f"  - Linhas: {len(payload.get('rows', []))}")
    print(f"  - Coluna de contato: {payload.get('contact_column')}")
    print(f"  - Coluna de arquivo: {payload.get('file_column', 'N/A')}")
    print(f"  - Anexar a todos: {payload.get('attach_to_all')}")
    
    channel = payload.get('channel', 'email')
    if channel not in ('email', 'whatsapp'):
        return JsonResponse({'error': 'Invalid channel'}, status=400)

    # Validate required fields from the new payload structure
    rows = payload.get('rows', [])
    contact_column = payload.get('contact_column', '')
    message = payload.get('message', '')
    subject = payload.get('subject', '')
    file_column = payload.get('file_column', '')
    attach_to_all = payload.get('attach_to_all', False)
    # attachment_names is set in multipart handling; use the one from payload
    if 'attachment_names' not in payload:
        payload['attachment_names'] = []

    if not contact_column:
        return JsonResponse({"error": "contact_column is required"}, status=400)
    if not message and channel == 'whatsapp':
        return JsonResponse({"error": "message is required for WhatsApp"}, status=400)
    if not subject and channel == 'email':
        return JsonResponse({"error": "subject is required for Email"}, status=400)
    if not rows:
        return JsonResponse({"error": "rows is required"}, status=400)
    
    # Validate channel-specific authentication
    if channel == 'email':
        email_sender = payload.get('email_sender')
        app_password = payload.get('app_password')
        if not email_sender:
            return JsonResponse({"error": "email_sender is required for email channel"}, status=400)
        if not app_password:
            return JsonResponse({"error": "app_password is required for email channel"}, status=400)
        print(f"  - Remetente (email): {email_sender}")
    else:  # whatsapp
        phone_number = payload.get('phone_number')
        if not phone_number:
            return JsonResponse({"error": "phone_number is required for WhatsApp channel"}, status=400)
        print(f"  - Número (WhatsApp): {phone_number}")

    # Delegate to service implementations
    from .services.email_service import EmailService
    from .services.whatsapp_service import WhatsAppService

    if channel == 'email':
        response = EmailService.send(payload)
    else:
        response = WhatsAppService.send(payload)

    print(f"[BACKEND] Resposta enviada com {len(response.get('previews', []))} previews")
    print(f"{'='*80}\n")
    
    return JsonResponse(response, status=202)



@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def whatsapp_test_view(request):
    """
    Endpoint para testar conexão com API do WhatsApp/Meta
    
    POST /api/whatsapp/test/
    
    Body (opcional):
    {
        "phone_number": "5541997393566",
        "template_name": "jaspers_market_plain_text_v1",
        "language_code": "en_US"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    
    phone_number = data.get('phone_number', '5541997393566')
    template_name = data.get('template_name', 'jaspers_market_plain_text_v1')
    language_code = data.get('language_code', 'en_US')
    
    print(f"\n{'='*80}")
    print(f"[WHATSAPP TEST] Testando envio via endpoint")
    print(f"[WHATSAPP TEST] Número: {phone_number}")
    print(f"[WHATSAPP TEST] Template: {template_name}")
    print(f"{'='*80}\n")
    
    result = WhatsAppAPI.send_template_message(
        to_number=phone_number,
        template_name=template_name,
        language_code=language_code
    )
    
    status_code = 200 if result.get('success') else 400
    return JsonResponse(result, status=status_code)


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_view(request):
    """
    Webhook endpoint to receive WhatsApp events from Meta
    
    POST /api/whatsapp/webhook/
    
    Events:
    - messages: incoming messages
    - statuses: message delivery status updates
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    print(f"\n{'='*80}")
    print(f"[WEBHOOK] Evento recebido de {request.META.get('HTTP_ORIGIN', 'UNKNOWN')}")
    print(f"{'='*80}")



@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def jobs_start_view(request):
    """Start a background send job (returns job_id)."""
    # Accept JSON or multipart/form-data same as send endpoints
    if request.content_type and request.content_type.startswith('multipart/'):
        payload_raw = request.POST.get('payload')
        if not payload_raw:
            return HttpResponseBadRequest('Missing payload in multipart form')
        
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON in payload field')
        
        files_bytes = {}
        for key in request.FILES:
            file_list = request.FILES.getlist(key)
            files_bytes[key] = []
            for f in file_list:
                f.seek(0)
                content = f.read()
                files_bytes[key].append({
                    'name': f.name,
                    'content': content,
                    'size': len(content)
                })
        
        payload['_files'] = files_bytes
    else:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON')

    # minimal validation
    contact_column = payload.get('contact_column')
    
    if not contact_column:
        return JsonResponse({'error': 'contact_column is required'}, status=400)

    owner_email = request.user.email
    
    job_id = job_manager.create_job(payload, owner_email)
    
    # start background thread
    job_manager.run_job_in_thread(job_id)

    return JsonResponse({'job_id': job_id, 'status': 'started'}, status=202)


@require_http_methods(["GET"])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def jobs_status_view(request, job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return JsonResponse({'error': 'job not found'}, status=404)
    # ensure only owner can see or keep simple for now
    return JsonResponse({
        'job_id': job['job_id'],
        'state': job['state'],
        'total': job['total'],
        'processed': job['processed'],
        'success': job['success'],
        'failed': job['failed'],
        'items': job['items'][-50:],
        'error': job['error'],
        'created_at': job['created_at'],
        'updated_at': job['updated_at']
    })


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def jobs_cancel_view(request, job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return JsonResponse({'error': 'job not found'}, status=404)
    job_manager.cancel_job(job_id)
    return JsonResponse({'job_id': job_id, 'status': 'canceled'})
    
    # Log the event
    log_webhook_event(data)
    
    # Parse the event
    events = parse_webhook_event(data)
    
    if events:
        print(f"[WEBHOOK] {len(events)} evento(s) processado(s)")
        for event in events:
            print(f"[WEBHOOK] Tipo: {event.get('type')}")
            if event.get('type') == 'message':
                print(f"  - De: {event.get('from')}")
                print(f"  - Mensagem: {event.get('text')}")
            elif event.get('type') == 'status_update':
                print(f"  - Status: {event.get('status')}")
                if event.get('error'):
                    print(f"  - Erro: {event['error'].get('message')}")
    
    print(f"{'='*80}\n")
    
    # Always return 200 to acknowledge receipt
    return JsonResponse({'status': 'received'}, status=200)


@require_http_methods(["GET"])
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def whatsapp_webhook_verify_view(request):
    """
    Webhook verification endpoint
    Meta calls this to verify the webhook URL
    
    GET /api/whatsapp/webhook/?hub.mode=subscribe&hub.challenge=xxx&hub.verify_token=xxx
    """
    mode = request.GET.get('hub.mode')
    challenge = request.GET.get('hub.challenge')
    verify_token = request.GET.get('hub.verify_token')
    
    print(f"\n[WEBHOOK VERIFY] mode={mode}, verify_token={verify_token}")
    
    # You should set this in your environment
    expected_token = 'seu_token_de_verificacao_aqui'
    
    if mode == 'subscribe' and verify_token == expected_token:
        print(f"[WEBHOOK VERIFY] Token valido! Webhook verificado.")
        return JsonResponse(challenge, status=200, safe=False)
    else:
        print(f"[WEBHOOK VERIFY] Token invalido!")
        return JsonResponse({'error': 'Unauthorized'}, status=403)


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def whatsapp_setup_view(request):
    """
    Setup WhatsApp phone number
    
    POST /api/whatsapp/setup/
    
    Body:
    {
        "waba_id": "your_waba_id"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    waba_id = data.get('waba_id')
    
    if not waba_id:
        return JsonResponse({'error': 'waba_id is required'}, status=400)
    
    print(f"\n[SETUP] Iniciando configuracao do WhatsApp...")
    print(f"[SETUP] WABA ID: {waba_id}")
    
    result = WhatsAppAPI.setup_phone_number(waba_id)
    
    status_code = 200 if all(r.get('success') for r in result['steps'].values()) else 400
    return JsonResponse(result, status=status_code)
