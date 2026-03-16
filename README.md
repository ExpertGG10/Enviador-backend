# enviador-backend

Projeto base em Django com endpoints mínimos para um "Enviador de Emails".

## Objetivo
Fornecer um esqueleto backend em Django com endpoints básicos:
- GET /api/health - status
- POST /api/send/ - endpoint genérico para envio (aceita `channel: email|whatsapp`)

Exemplos de payloads:
- Email:
```
POST /api/send/
{
  "channel": "email",
  "to": "a@example.com",
  "subject": "Olá",
  "body": "Corpo do email"
}
```
- WhatsApp:
```
POST /api/send/
{
  "channel": "whatsapp",
  "to": "+551199999999",
  "message": "Mensagem via WhatsApp"
}
```

## Requisitos
- Python 3.10+
- (Opcional) virtualenv/venv

## Setup rápido
1. python -m venv .venv
2. .\.venv\Scripts\activate
3. pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py runserver

## Testes
- python manage.py test

## Banco local de testes
- O projeto usa um banco separado para testes automatizados: `db_test.sqlite3`.
- Para customizar, defina `TEST_DATABASE_URL` no ambiente (exemplo: `sqlite:///db_test.sqlite3`).
- O banco de producao continua vindo de `DATABASE_URL`.

Exemplo (PowerShell):
```powershell
$env:TEST_DATABASE_URL = "sqlite:///db_test.sqlite3"
python manage.py test
```
