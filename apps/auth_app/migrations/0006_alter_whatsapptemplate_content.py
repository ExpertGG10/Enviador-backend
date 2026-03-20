from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0005_delete_accountsettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='whatsapptemplate',
            name='content',
            field=models.TextField(blank=True, default=''),
        ),
    ]
