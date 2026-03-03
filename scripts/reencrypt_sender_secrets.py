import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enviador.settings')

import django

django.setup()

from apps.auth_app.models import GmailSender, WhatsAppSender
from shared.utils.crypto import decrypt_password


def is_encrypted(value: str) -> bool:
    if not value:
        return False
    try:
        decrypt_password(value)
        return True
    except Exception:
        return False


g_total = 0
g_fixed = 0
for sender in GmailSender.objects.exclude(app_password_encrypted=''):
    g_total += 1
    if not is_encrypted(sender.app_password_encrypted):
        sender.set_app_password(sender.app_password_encrypted)
        sender.save(update_fields=['app_password_encrypted', 'updated_at'])
        g_fixed += 1

w_total = 0
w_fixed = 0
for sender in WhatsAppSender.objects.exclude(access_token_encrypted=''):
    w_total += 1
    if not is_encrypted(sender.access_token_encrypted):
        sender.set_access_token(sender.access_token_encrypted)
        sender.save(update_fields=['access_token_encrypted', 'updated_at'])
        w_fixed += 1

print({
    'gmail_total': g_total,
    'gmail_reencrypted': g_fixed,
    'whatsapp_total': w_total,
    'whatsapp_reencrypted': w_fixed,
})
