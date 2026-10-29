from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_brigadistas_usuarios'),
    ]

    operations = [
        migrations.RenameField(
            model_name='brigada',
            old_name='lotacao',
            new_name='endereco',
        ),
        migrations.AlterField(
            model_name='brigada',
            name='endereco',
            field=models.CharField(max_length=150, verbose_name='Endereço'),
        ),
        migrations.RemoveField(
            model_name='brigada',
            name='tipo',
        ),
        migrations.RemoveField(
            model_name='brigada',
            name='regiao',
        ),
        migrations.RemoveField(
            model_name='brigada',
            name='efetivo_previsto',
        ),
        migrations.RemoveField(
            model_name='brigada',
            name='status',
        ),
    ]
