from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Brigada


class LoginFlowTest(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username='brigadista', password='senha123')

    def test_raiz_redireciona_para_login_quando_nao_autenticado(self):
        response = self.client.get('/')

        self.assertRedirects(response, reverse('login'))

    def test_home_requer_autenticacao(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/login/?next={reverse('home')}", response.url)

    def test_pagina_de_login_renderiza_campos(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username')
        self.assertContains(response, 'password')

    def test_cadastro_de_usuario_cria_conta_e_redireciona_para_home(self):
        response = self.client.post(
            reverse('cadastro_usuario'),
            {
                'username': 'novo.usuario',
                'email': 'novo@teste.com',
                'password1': 'SenhaForte123!',
                'password2': 'SenhaForte123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user_model.objects.filter(username='novo.usuario').exists())
        self.assertContains(response, 'Cadastro Estadual de Brigadas')


class BrigadaCadastroTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='brigadista', password='senha123')
        self.client = Client()
        self.client.force_login(self.user)

    def test_home_exibe_formulario_de_brigada_com_coordenadas(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coordenada da brigada')
        self.assertContains(response, 'name="cep"')
        self.assertContains(response, 'brigadista_cpf[]')
        self.assertContains(response, 'name="latitude"')
        self.assertContains(response, 'name="longitude"')
        self.assertContains(response, 'openstreetmap.de')
        self.assertContains(response, 'Lista de brigadistas')

    def test_home_renderiza_campo_oculto_de_brigadistas_sem_required(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, '<textarea name="brigadistas"')
        self.assertNotContains(response, 'required id="id_brigadistas"')

    def test_home_exibe_nome_do_usuario(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'brigadista')
        self.assertNotContains(response, '<span>Usuário</span>')

    def test_home_exibe_formulario_e_salva_brigada(self):
        response = self.client.post(
            reverse('home'),
            {
                'nome': 'Brigada de Incêndio Urbano',
                'tipo': 'incendio',
                'regiao': 'Sul',
                'municipio': 'Criciúma',
                'lotacao': 'Base Central',
                'cep': '88010-000',
                'latitude': '-27.5',
                'longitude': '-48.5',
                'efetivo_previsto': 18,
                'status': 'ativa',
                'observacoes': 'Equipe de resposta rápida.',
                'brigadistas': 'Maria Silva - Capitã\nJoão Pereira - Bombeiro',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brigada.objects.filter(nome='Brigada de Incêndio Urbano', cep='88010-000').exists())

    def _dados_validos(self, **extra):
        dados = {
            'nome': 'Brigada Centro',
            'lotacao': 'Rua A, 10',
            'cep': '40000-000',
            'latitude': '-12.97',
            'longitude': '-38.5',
            'brigadistas': 'Maria Silva | maria@teste.com | 000.000.000-00 | 71999990000',
        }
        dados.update(extra)
        return dados

    def test_salvar_brigada_exibe_mensagem_de_sucesso(self):
        response = self.client.post(reverse('home'), self._dados_validos(), follow=True)

        self.assertContains(response, 'Brigada &quot;Brigada Centro&quot; cadastrada com sucesso.')

    def test_brigada_sem_brigadistas_exibe_erro_e_nao_salva(self):
        response = self.client.post(reverse('home'), self._dados_validos(brigadistas=''))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Adicione ao menos um brigadista à lista.')
        self.assertFalse(Brigada.objects.exists())

    def test_coordenadas_fora_da_faixa_sao_rejeitadas(self):
        response = self.client.post(reverse('home'), self._dados_validos(latitude='-95', longitude='200'))

        self.assertContains(response, 'A latitude deve estar entre -90 e 90.')
        self.assertContains(response, 'A longitude deve estar entre -180 e 180.')
        self.assertFalse(Brigada.objects.exists())

    def test_formulario_reexibido_mantem_brigadistas_escapados(self):
        response = self.client.post(
            reverse('home'),
            self._dados_validos(nome='', brigadistas='<script>alert(1)</script> | x@y.com'),
        )

        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
