from django.db import migrations


def ensure_accountsettings_table(apps, schema_editor):
    AccountSettings = apps.get_model('auth_app', 'AccountSettings')
    table_name = AccountSettings._meta.db_table

    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name not in existing_tables:
        schema_editor.create_model(AccountSettings)


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0003_migrate_legacy_account_settings'),
    ]

    operations = [
        migrations.RunPython(ensure_accountsettings_table, migrations.RunPython.noop),
    ]
