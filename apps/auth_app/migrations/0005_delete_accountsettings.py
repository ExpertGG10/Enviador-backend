from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0004_remove_legacy_accountsettings_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AccountSettings',
        ),
    ]
