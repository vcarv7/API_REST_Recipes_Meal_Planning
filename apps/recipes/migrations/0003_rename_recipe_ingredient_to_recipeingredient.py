from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0002_rename_related_names_add_unique_constraint'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Recipe_Ingredient',
            new_name='RecipeIngredient',
        ),
    ]
