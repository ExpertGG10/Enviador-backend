from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0006_alter_whatsapptemplate_content'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='whatsapptemplate',
            name='content',
        ),
    ]