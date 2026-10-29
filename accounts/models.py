from django.conf import settings
from django.db import models


class Brigada(models.Model):
    nome = models.CharField('Nome da brigada', max_length=200)
    municipio = models.CharField('Município', max_length=100, blank=True, null=True)
    endereco = models.CharField('Endereço', max_length=150)
    cep = models.CharField('CEP', max_length=9, blank=True)
    latitude = models.FloatField('Latitude', blank=True, null=True)
    longitude = models.FloatField('Longitude', blank=True, null=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brigadas_criadas',
        verbose_name='Criada por',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    nome_completo = models.CharField('Nome completo', max_length=200)
    cpf = models.CharField('CPF', max_length=11, unique=True, help_text='Somente os 11 dígitos.')
    brigada = models.ForeignKey(
        Brigada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brigadistas',
        verbose_name='Brigada',
    )
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    numero_calcado = models.PositiveSmallIntegerField('Número do calçado', blank=True, null=True)
    tamanho_blusa = models.CharField('Tamanho da blusa', max_length=5, blank=True)
    tamanho_calca = models.CharField('Tamanho da calça', max_length=5, blank=True)

    def __str__(self):
        return self.nome_completo


def conta_protegida(usuario):
    """Contas que nunca são apagadas nem alteradas pela lista de brigadistas:
    administradores e responsáveis que criaram alguma brigada."""
    return usuario.is_staff or usuario.is_superuser or usuario.brigadas_criadas.exists()


def retirar_da_brigada(perfis):
    """Brigadista não existe fora de brigada: a conta de quem sai é apagada.
    Contas protegidas apenas ficam sem brigada."""
    for perfil in perfis.select_related('usuario'):
        if conta_protegida(perfil.usuario):
            perfil.brigada = None
            perfil.save(update_fields=['brigada'])
        else:
            perfil.usuario.delete()
