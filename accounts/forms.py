import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from .geo import ponto_na_bahia
from .models import Brigada, Perfil, conta_protegida, retirar_da_brigada


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
    """Cadastro da brigada. Cada brigadista da lista vira um usuário do sistema:
    quem já tem conta (mesmo e-mail ou CPF) é vinculado; os demais ganham uma
    conta sem senha, que pode ser definida depois pelo "esqueci minha senha"."""

    COLUNAS_BRIGADISTA = ('nome', 'email', 'cpf', 'telefone', 'calcado', 'blusa', 'calca')

    brigadistas = forms.CharField(
        label='Lista de brigadistas',
        widget=HiddenTextarea(attrs={'class': 'hidden-textarea'}),
        error_messages={'required': 'Adicione ao menos um brigadista à lista.'},
    )

    class Meta:
        model = Brigada
        fields = [
            'nome',
            'endereco',
            'cep',
            'latitude',
            'longitude',
            'municipio',
        ]
        labels = {
            'nome': 'Nome',
            'endereco': 'Endereço',
            'cep': 'CEP',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'municipio': 'Município',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome da brigada'}),
            'endereco': forms.TextInput(attrs={'placeholder': 'Endereço'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000-000', 'inputmode': 'numeric', 'autocomplete': 'postal-code', 'maxlength': 9}),
            'latitude': forms.TextInput(attrs={'placeholder': '-15.7939', 'inputmode': 'decimal'}),
            'longitude': forms.TextInput(attrs={'placeholder': '-47.8828', 'inputmode': 'decimal'}),
            'municipio': forms.TextInput(attrs={'placeholder': 'Preenchido ao marcar o ponto no mapa'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Na edição, a lista começa com os brigadistas já vinculados.
            linhas = []
            for perfil in self.instance.brigadistas.select_related('usuario').order_by('nome_completo'):
                valores = [
                    perfil.nome_completo,
                    perfil.usuario.email or perfil.usuario.username,
                    perfil.cpf,
                    perfil.telefone,
                    perfil.numero_calcado or '',
                    perfil.tamanho_blusa,
                    perfil.tamanho_calca,
                ]
                linhas.append(' | '.join(str(valor).replace('|', '/') for valor in valores))
            self.initial['brigadistas'] = '\n'.join(linhas)

    def clean_brigadistas(self):
        """Converte as linhas "nome | e-mail | CPF | telefone | calçado | blusa | calça"
        em dicionários, resolvendo o usuário já existente de cada brigadista."""
        linhas = [linha.strip() for linha in self.cleaned_data['brigadistas'].splitlines() if linha.strip()]
        brigadistas, erros = [], []
        emails_vistos, cpfs_vistos = set(), set()

        for numero, linha in enumerate(linhas, start=1):
            partes = [parte.strip() for parte in linha.split('|')]
            dados = dict(zip(self.COLUNAS_BRIGADISTA, partes + [''] * len(self.COLUNAS_BRIGADISTA)))
            nome = ' '.join(dados['nome'].split())
            rotulo = f'Brigadista {numero}' + (f' ({nome})' if nome else '')
            email = dados['email'].lower()
            cpf = re.sub(r'\D', '', dados['cpf'])
            erros_linha = []

            if not nome:
                erros_linha.append('informe o nome')
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError:
                erros_linha.append('informe um e-mail válido')
            if not cpf_valido(cpf):
                erros_linha.append('informe um CPF válido')

            calcado = None
            if dados['calcado']:
                if dados['calcado'].isdigit() and 15 <= int(dados['calcado']) <= 50:
                    calcado = int(dados['calcado'])
                else:
                    erros_linha.append('o número do calçado deve estar entre 15 e 50')

            telefone, blusa, calca = dados['telefone'][:20], dados['blusa'].upper(), dados['calca'].upper()
            if len(blusa) > 5 or len(calca) > 5:
                erros_linha.append('tamanho da blusa ou da calça inválido')

            if email in emails_vistos or cpf in cpfs_vistos:
                erros_linha.append('e-mail ou CPF repetido na lista')
            emails_vistos.add(email)
            cpfs_vistos.add(cpf)

            usuario = None
            if not erros_linha:
                usuario, erro = self._usuario_existente(email, cpf)
                if erro:
                    erros_linha.append(erro)

            if erros_linha:
                erros.append(f'{rotulo}: {"; ".join(erros_linha)}.')
                continue

            brigadistas.append({
                'usuario': usuario,
                'nome': nome,
                'email': email,
                'cpf': cpf,
                'telefone': telefone,
                'numero_calcado': calcado,
                'tamanho_blusa': blusa,
                'tamanho_calca': calca,
            })

        if erros:
            raise forms.ValidationError(erros)
        if not brigadistas:
            raise forms.ValidationError(self.fields['brigadistas'].error_messages['required'])
        return brigadistas

    def _usuario_existente(self, email, cpf):
        """Retorna (usuário, erro). O usuário é None quando ainda não há conta."""
        por_email = User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).first()
        perfil_cpf = Perfil.objects.select_related('usuario').filter(cpf=cpf).first()
        por_cpf = perfil_cpf.usuario if perfil_cpf else None

        if por_email and por_cpf and por_email != por_cpf:
            return None, 'o e-mail e o CPF pertencem a contas diferentes'
        usuario = por_email or por_cpf
        if usuario is None:
            return None, None

        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.cpf != cpf:
            return None, 'este e-mail já está cadastrado com outro CPF'
        # O e-mail da conta é trocado pelo da lista, exceto em contas protegidas.
        if por_cpf and email not in (usuario.email.lower(), usuario.username.lower()) and conta_protegida(usuario):
            return None, 'este CPF pertence a uma conta de administrador ou de responsável por brigada, cujo e-mail não pode ser trocado; informe o e-mail já cadastrado nessa conta'
        if perfil and perfil.brigada_id and perfil.brigada_id != self.instance.pk:
            return None, f'já faz parte da brigada "{perfil.brigada}"'
        return usuario, None

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError('BrigadaForm precisa salvar os brigadistas junto com a brigada.')
        brigada = super().save()
        usuarios = []
        for dados in self.cleaned_data['brigadistas']:
            usuario = dados['usuario']
            if usuario is None:
                primeiro_nome, _, sobrenome = dados['nome'].partition(' ')
                usuario = User(
                    username=dados['email'],
                    email=dados['email'],
                    first_name=primeiro_nome[:150],
                    last_name=sobrenome[:150],
                )
                usuario.set_unusable_password()
                usuario.save()
            elif dados['email'] not in (usuario.email.lower(), usuario.username.lower()):
                usuario.username = usuario.email = dados['email']
                usuario.save(update_fields=['username', 'email'])
            perfil, _ = Perfil.objects.get_or_create(
                usuario=usuario,
                defaults={'nome_completo': dados['nome'], 'cpf': dados['cpf']},
            )
            perfil.brigada = brigada
            perfil.telefone = dados['telefone']
            perfil.numero_calcado = dados['numero_calcado']
            perfil.tamanho_blusa = dados['tamanho_blusa']
            perfil.tamanho_calca = dados['tamanho_calca']
            perfil.save()
            usuarios.append(usuario)
        retirar_da_brigada(brigada.brigadistas.exclude(usuario__in=usuarios))
        return brigada

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
