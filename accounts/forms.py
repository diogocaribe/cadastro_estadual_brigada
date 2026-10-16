from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Brigada


class HiddenTextarea(forms.Textarea):
    """Textarea preenchida via JavaScript; sem o atributo HTML ``required``
    para que a validação nativa do navegador não bloqueie o envio de um
    campo invisível. A obrigatoriedade continua sendo validada no servidor."""

    def use_required_attribute(self, initial):
        return False


class CadastroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class BrigadaForm(forms.ModelForm):
    class Meta:
        model = Brigada
        fields = [
            'nome',
            'lotacao',
            'cep',
            'latitude',
            'longitude',
            'brigadistas',
        ]
        labels = {
            'nome': 'Nome',
            'lotacao': 'Endereço',
            'cep': 'CEP',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'brigadistas': 'Lista de brigadistas',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome da brigada'}),
            'lotacao': forms.TextInput(attrs={'placeholder': 'Endereço'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000-000'}),
            'latitude': forms.TextInput(attrs={'placeholder': '-15.7939', 'inputmode': 'decimal'}),
            'longitude': forms.TextInput(attrs={'placeholder': '-47.8828', 'inputmode': 'decimal'}),
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
