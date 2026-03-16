from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppOutboundMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('to_wa_id', models.CharField(db_index=True, max_length=40)),
                ('text_body', models.TextField()),
                ('whatsapp_message_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('phone_number_id', models.CharField(blank=True, max_length=80)),
                ('status', models.CharField(default='sent', max_length=40)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_outbound_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'WhatsApp Outbound Message',
                'verbose_name_plural': 'WhatsApp Outbound Messages',
                'ordering': ['-created_at'],
            },
        ),
    ]
