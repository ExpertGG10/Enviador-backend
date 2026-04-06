from django.db import migrations


def ensure_accountsettings_table(apps, schema_editor):
    try:
        AccountSettings = apps.get_model('auth_app', 'AccountSettings')
    except LookupError:
        # This branch can be applied after migrations that delete AccountSettings.
        # In that case, this repair step should be a harmless no-op.
        return

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
