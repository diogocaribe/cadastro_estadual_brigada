from django.db import models


class Brigada(models.Model):
    TIPO_CHOICES = [
        ('incendio', 'Incêndio'),
        ('resgate', 'Resgate'),
        ('ambulancia', 'Ambulância'),
        ('civil', 'Proteção Civil'),
        ('outros', 'Outros'),
    ]

    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('em_acionamento', 'Em acionamento'),
        ('inativa', 'Inativa'),
    ]

    nome = models.CharField('Nome da brigada', max_length=200)
    tipo = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES, blank=True, null=True)
    regiao = models.CharField('Região', max_length=100, blank=True, null=True)
    municipio = models.CharField('Município', max_length=100, blank=True, null=True)
    lotacao = models.CharField('Lotação', max_length=150)
    cep = models.CharField('CEP', max_length=9, blank=True)
    latitude = models.FloatField('Latitude', blank=True, null=True)
    longitude = models.FloatField('Longitude', blank=True, null=True)
    efetivo_previsto = models.PositiveIntegerField('Efetivo previsto', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativa')
    observacoes = models.TextField('Observações', blank=True)
    brigadistas = models.TextField('Lista de brigadistas', help_text='Informe um brigadista por linha.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def lista_brigadistas(self):
        return [linha.strip() for linha in self.brigadistas.splitlines() if linha.strip()]

    def __str__(self):
        return self.nome
