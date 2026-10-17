from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('plan', '0004_planmeal'),
    ]

    operations = [
        migrations.RenameField(
            model_name='plan',
            old_name='start_Date',
            new_name='start_date',
        ),
        migrations.RenameField(
            model_name='plan',
            old_name='end_Date',
            new_name='end_date',
        ),
    ]
