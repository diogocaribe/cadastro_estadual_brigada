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

    def _dados_cadastro(self, **extra):
        dados = {
            'nome_completo': 'Maria  da Silva Souza',
            'cpf': '529.982.247-25',
            'email': 'Maria@Teste.com',
            'password1': 'SenhaForte123!',
            'password2': 'SenhaForte123!',
        }
        dados.update(extra)
        return dados

    def test_cadastro_de_usuario_cria_conta_e_redireciona_para_home(self):
        response = self.client.post(reverse('cadastro_usuario'), self._dados_cadastro(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cadastro Estadual de Brigadas')
        user = self.user_model.objects.get(username='maria@teste.com')
        self.assertEqual(user.email, 'maria@teste.com')
        self.assertEqual(user.perfil.nome_completo, 'Maria da Silva Souza')
        self.assertEqual(user.perfil.cpf, '52998224725')
        self.assertEqual((user.first_name, user.last_name), ('Maria', 'da Silva Souza'))

    def test_pagina_de_cadastro_exibe_nome_completo_e_cpf(self):
        response = self.client.get(reverse('cadastro_usuario'))

        self.assertContains(response, 'name="nome_completo"')
        self.assertContains(response, 'name="cpf"')
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'name="username"')

    def test_cadastro_rejeita_cpf_invalido(self):
        for cpf in ('123.456.789-00', '111.111.111-11', '5299822472'):
            response = self.client.post(reverse('cadastro_usuario'), self._dados_cadastro(cpf=cpf))
            self.assertContains(response, 'Informe um CPF válido.')
        self.assertFalse(self.user_model.objects.filter(username='maria@teste.com').exists())

    def test_cadastro_rejeita_cpf_repetido(self):
        self.client.post(reverse('cadastro_usuario'), self._dados_cadastro())
        self.client.logout()

        response = self.client.post(reverse('cadastro_usuario'), self._dados_cadastro(email='outra@teste.com', cpf='52998224725'))

        self.assertContains(response, 'Já existe uma conta com este CPF.')

    def test_cadastro_rejeita_email_repetido_sem_diferenciar_maiusculas(self):
        self.client.post(reverse('cadastro_usuario'), self._dados_cadastro())
        self.client.logout()

        response = self.client.post(reverse('cadastro_usuario'), self._dados_cadastro(email='MARIA@teste.com', cpf='111.444.777-35'))

        self.assertContains(response, 'Já existe uma conta com este e-mail.')

    def test_login_com_email_sem_diferenciar_maiusculas(self):
        self.client.post(reverse('cadastro_usuario'), self._dados_cadastro())
        self.client.logout()

        response = self.client.post(reverse('login'), {'username': ' MARIA@teste.com ', 'password': 'SenhaForte123!'})

        self.assertRedirects(response, reverse('home'))

    def test_login_de_conta_antiga_pelo_usuario_continua_funcionando(self):
        response = self.client.post(reverse('login'), {'username': 'brigadista', 'password': 'senha123'})

        self.assertRedirects(response, reverse('home'))


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
        self.assertContains(response, 'brigadista_calcado[]')
        self.assertContains(response, 'brigadista_blusa[]')
        self.assertContains(response, 'brigadista_calca[]')
        self.assertContains(response, 'name="latitude"')
        self.assertContains(response, 'name="longitude"')
        self.assertContains(response, 'tile.openstreetmap.org')
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
                'municipio': 'Salvador',
                'lotacao': 'Base Central',
                'cep': '88010-000',
                'latitude': '-12.97',
                'longitude': '-38.5',
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

    def test_coordenada_fora_da_bahia_nao_salva(self):
        # Florianópolis (SC)
        response = self.client.post(reverse('home'), self._dados_validos(latitude='-27.59', longitude='-48.55'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A coordenada informada está fora da Bahia.')
        self.assertFalse(Brigada.objects.exists())

    def test_coordenada_no_oceano_proximo_a_salvador_nao_salva(self):
        response = self.client.post(reverse('home'), self._dados_validos(latitude='-13.2', longitude='-38.2'))

        self.assertContains(response, 'A coordenada informada está fora da Bahia.')
        self.assertFalse(Brigada.objects.exists())

    def test_latitude_sem_longitude_nao_salva(self):
        response = self.client.post(reverse('home'), self._dados_validos(longitude=''))

        self.assertContains(response, 'Informe a latitude e a longitude juntas.')
        self.assertFalse(Brigada.objects.exists())

    def test_brigada_sem_coordenadas_continua_permitida(self):
        self.client.post(reverse('home'), self._dados_validos(latitude='', longitude=''))

        self.assertTrue(Brigada.objects.filter(nome='Brigada Centro').exists())

    def test_limite_da_bahia_e_servido_como_geojson(self):
        response = self.client.get(reverse('limite_bahia'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/geo+json')
        self.assertIn(b'"FeatureCollection"', b''.join(response.streaming_content))

    def test_ponto_na_bahia(self):
        from accounts.geo import ponto_na_bahia

        self.assertTrue(ponto_na_bahia(-12.97, -38.5))  # Salvador
        self.assertTrue(ponto_na_bahia(-9.42, -40.50))  # Juazeiro
        self.assertTrue(ponto_na_bahia(-17.54, -39.74))  # Teixeira de Freitas
        self.assertFalse(ponto_na_bahia(-9.39, -40.50))  # Petrolina (PE)
        self.assertFalse(ponto_na_bahia(-15.79, -47.88))  # Brasília
        self.assertFalse(ponto_na_bahia(-13.2, -38.2))  # Oceano

    def test_salvar_brigada_grava_municipio(self):
        self.client.post(reverse('home'), self._dados_validos(municipio='Salvador'))

        self.assertEqual(Brigada.objects.get(nome='Brigada Centro').municipio, 'Salvador')

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


class AdminTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('admin', 'admin@teste.com', 'senha123')
        self.client.force_login(self.admin)

    def test_lista_de_usuarios_exibe_nome_e_cpf(self):
        self.client.logout()
        self.client.post(reverse('cadastro_usuario'), {
            'nome_completo': 'Maria da Silva', 'cpf': '529.982.247-25', 'email': 'maria@teste.com',
            'password1': 'SenhaForte123!', 'password2': 'SenhaForte123!',
        })
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin:auth_user_changelist'), {'q': '52998224725'})

        self.assertContains(response, 'Maria da Silva')
        self.assertContains(response, '529.982.247-25')

    def test_telas_do_admin_abrem(self):
        for url in (
            reverse('admin:index'),
            reverse('admin:auth_user_change', args=[self.admin.pk]),
            reverse('admin:auth_user_add'),
            reverse('admin:accounts_brigada_changelist'),
            reverse('admin:accounts_perfil_changelist'),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_exige_staff(self):
        self.client.logout()
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
