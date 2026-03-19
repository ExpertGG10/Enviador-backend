from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0003_migrate_legacy_account_settings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accountsettings',
            name='gmail_app_password',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='gmail_sender_email',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='whatsapp_access_token',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='whatsapp_business_id',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='whatsapp_phone_number',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='whatsapp_phone_number_id',
        ),
        migrations.RemoveField(
            model_name='accountsettings',
            name='whatsapp_templates',
        ),
    ]
