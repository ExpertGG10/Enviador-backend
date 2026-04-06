from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0007_remove_whatsapptemplate_content'),
    ]

    operations = [
        migrations.RenameField(
            model_name='whatsappsender',
            old_name='business_id',
            new_name='waba_id',
        ),
    ]