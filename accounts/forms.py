import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from .geo import ponto_na_bahia
from .models import Brigada, Perfil


class HiddenTextarea(forms.Textarea):
    """Textarea preenchida via JavaScript; sem o atributo HTML ``required``
    para que a validação nativa do navegador não bloqueie o envio de um
    campo invisível. A obrigatoriedade continua sendo validada no servidor."""

    def use_required_attribute(self, initial):
        return False


def cpf_valido(cpf):
    """Confere os dígitos verificadores de um CPF com 11 dígitos."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(cpf[i]) * (posicao + 1 - i) for i in range(posicao))
        if (soma * 10) % 11 % 10 != int(cpf[posicao]):
            return False
    return True


class CadastroUsuarioForm(UserCreationForm):
    """Cadastro em que o e-mail é o nome de usuário usado no login."""

    nome_completo = forms.CharField(
        label='Nome completo',
        max_length=200,
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'autofocus': True}),
    )
    cpf = forms.CharField(
        label='CPF',
        max_length=14,
        widget=forms.TextInput(attrs={'placeholder': '000.000.000-00', 'inputmode': 'numeric'}),
    )
    email = forms.EmailField(
        label='E-mail',
        help_text='Será usado para entrar no sistema.',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'nome@exemplo.com'}),
    )

    field_order = ['nome_completo', 'cpf', 'email', 'password1', 'password2']

    class Meta:
        model = User
        fields = ('email',)

    def clean_nome_completo(self):
        return ' '.join(self.cleaned_data['nome_completo'].split())

    def clean_cpf(self):
        cpf = re.sub(r'\D', '', self.cleaned_data['cpf'])
        if not cpf_valido(cpf):
            raise forms.ValidationError('Informe um CPF válido.')
        if Perfil.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError('Já existe uma conta com este CPF.')
        return cpf

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise forms.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        nome = self.cleaned_data['nome_completo']
        primeiro_nome, _, sobrenome = nome.partition(' ')
        user.username = email
        user.email = email
        user.first_name = primeiro_nome[:150]
        user.last_name = sobrenome[:150]
        if commit:
            with transaction.atomic():
                user.save()
                Perfil.objects.create(usuario=user, nome_completo=nome, cpf=self.cleaned_data['cpf'])
        return user


class LoginForm(AuthenticationForm):
    """Login pelo e-mail. Contas antigas, sem '@' no usuário, continuam entrando."""

    username = UsernameField(
        label='E-mail',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'email', 'placeholder': 'nome@exemplo.com'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        return username.lower() if '@' in username else username


class BrigadaForm(forms.ModelForm):
    class Meta:
        model = Brigada
        fields = [
            'nome',
            'lotacao',
            'cep',
            'latitude',
            'longitude',
            'municipio',
            'brigadistas',
        ]
        labels = {
            'nome': 'Nome',
            'lotacao': 'Endereço',
            'cep': 'CEP',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'municipio': 'Município',
            'brigadistas': 'Lista de brigadistas',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome da brigada'}),
            'lotacao': forms.TextInput(attrs={'placeholder': 'Endereço'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000-000'}),
            'latitude': forms.TextInput(attrs={'placeholder': '-15.7939', 'inputmode': 'decimal'}),
            'longitude': forms.TextInput(attrs={'placeholder': '-47.8828', 'inputmode': 'decimal'}),
            'municipio': forms.TextInput(attrs={'placeholder': 'Preenchido ao marcar o ponto no mapa'}),
            'brigadistas': HiddenTextarea(attrs={'class': 'hidden-textarea'}),
        }
        error_messages = {
            'brigadistas': {'required': 'Adicione ao menos um brigadista à lista.'},
        }

    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None and not -90 <= latitude <= 90:
            raise forms.ValidationError('A latitude deve estar entre -90 e 90.')
        return latitude

    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None and not -180 <= longitude <= 180:
            raise forms.ValidationError('A longitude deve estar entre -180 e 180.')
        return longitude

    def clean(self):
        cleaned_data = super().clean()
        if self.has_error('latitude') or self.has_error('longitude'):
            return cleaned_data

        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Informe a latitude e a longitude juntas.')
        if latitude is not None and not ponto_na_bahia(latitude, longitude):
            raise forms.ValidationError('A coordenada informada está fora da Bahia.')
        return cleaned_data
