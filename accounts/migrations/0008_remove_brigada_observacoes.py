from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_brigada_endereco_remove_campos'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='brigada',
            name='observacoes',
        ),
    ]
