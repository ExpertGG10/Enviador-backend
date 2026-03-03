from django.db import migrations


def _safe_encrypt(value: str):
    if not value:
        return ''

    try:
        from shared.utils.crypto import encrypt_password
        return encrypt_password(value)
    except Exception:
        return value


def migrate_legacy_account_settings(apps, schema_editor):
    AccountSettings = apps.get_model('auth_app', 'AccountSettings')
    GmailSender = apps.get_model('auth_app', 'GmailSender')
    WhatsAppSender = apps.get_model('auth_app', 'WhatsAppSender')
    WhatsAppTemplate = apps.get_model('auth_app', 'WhatsAppTemplate')

    for settings_obj in AccountSettings.objects.select_related('user').all():
        user = settings_obj.user

        gmail_sender = None
        if settings_obj.gmail_sender_email:
            gmail_sender, _ = GmailSender.objects.get_or_create(
                user=user,
                sender_email=settings_obj.gmail_sender_email,
                defaults={
                    'app_password_encrypted': _safe_encrypt(settings_obj.gmail_app_password),
                }
            )

            if not gmail_sender.app_password_encrypted and settings_obj.gmail_app_password:
                gmail_sender.app_password_encrypted = _safe_encrypt(settings_obj.gmail_app_password)
                gmail_sender.save(update_fields=['app_password_encrypted', 'updated_at'])

        whatsapp_sender = None
        if settings_obj.whatsapp_phone_number:
            whatsapp_sender, _ = WhatsAppSender.objects.get_or_create(
                user=user,
                phone_number=settings_obj.whatsapp_phone_number,
                defaults={
                    'access_token_encrypted': _safe_encrypt(settings_obj.whatsapp_access_token),
                    'phone_number_id': settings_obj.whatsapp_phone_number_id or '',
                    'business_id': settings_obj.whatsapp_business_id or '',
                }
            )

            if not whatsapp_sender.access_token_encrypted and settings_obj.whatsapp_access_token:
                whatsapp_sender.access_token_encrypted = _safe_encrypt(settings_obj.whatsapp_access_token)
                whatsapp_sender.save(update_fields=['access_token_encrypted', 'updated_at'])

        if whatsapp_sender and isinstance(settings_obj.whatsapp_templates, list):
            for template_title in settings_obj.whatsapp_templates:
                if not template_title or not isinstance(template_title, str):
                    continue
                WhatsAppTemplate.objects.get_or_create(
                    sender=whatsapp_sender,
                    title=template_title,
                    defaults={
                        'content': template_title,
                    }
                )


def reverse_migration(apps, schema_editor):
    # Mantém irreversível para evitar sobrescrever dados legados já ajustados manualmente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0002_gmail_whatsapp_senders_templates'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_account_settings, reverse_migration),
    ]
