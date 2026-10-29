from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Brigada, Perfil


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
        self.assertContains(response, 'viacep.com.br/ws/')
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
                'municipio': 'Salvador',
                'endereco': 'Base Central',
                'cep': '88010-000',
                'latitude': '-12.97',
                'longitude': '-38.5',
                'brigadistas': (
                    'Maria Silva | maria@teste.com | 529.982.247-25 | 71999990000 | 37 | M | 40\n'
                    'João Pereira | joao@teste.com | 111.444.777-35 | 71988880000 | 42 | G | 44'
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brigada.objects.filter(nome='Brigada de Incêndio Urbano', cep='88010-000').exists())

    def _dados_validos(self, **extra):
        dados = {
            'nome': 'Brigada Centro',
            'endereco': 'Rua A, 10',
            'cep': '40000-000',
            'latitude': '-12.97',
            'longitude': '-38.5',
            'brigadistas': 'Maria Silva | maria@teste.com | 529.982.247-25 | 71999990000',
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

    def test_brigadistas_viram_usuarios_vinculados_a_brigada(self):
        self.client.post(reverse('home'), self._dados_validos(
            brigadistas='Maria  da Silva | Maria@Teste.com | 529.982.247-25 | (71) 99999-0000 | 37 | m | 40',
        ))

        brigada = Brigada.objects.get(nome='Brigada Centro')
        perfil = Perfil.objects.get(cpf='52998224725')
        self.assertEqual(perfil.brigada, brigada)
        self.assertEqual(perfil.nome_completo, 'Maria da Silva')
        self.assertEqual(perfil.telefone, '(71) 99999-0000')
        self.assertEqual(perfil.numero_calcado, 37)
        self.assertEqual(perfil.tamanho_blusa, 'M')
        self.assertEqual(perfil.tamanho_calca, '40')
        self.assertEqual(perfil.usuario.username, 'maria@teste.com')
        self.assertEqual(perfil.usuario.email, 'maria@teste.com')
        self.assertFalse(perfil.usuario.has_usable_password())
        self.assertQuerySetEqual(brigada.brigadistas.all(), [perfil])

    def test_brigadista_com_conta_existente_e_vinculado_sem_duplicar(self):
        existente = get_user_model().objects.create_user('maria@teste.com', 'maria@teste.com', 'SenhaForte123!')
        Perfil.objects.create(usuario=existente, nome_completo='Maria da Silva', cpf='52998224725')

        self.client.post(reverse('home'), self._dados_validos())

        existente.refresh_from_db()
        self.assertEqual(existente.perfil.brigada.nome, 'Brigada Centro')
        self.assertEqual(existente.perfil.telefone, '71999990000')
        self.assertTrue(existente.check_password('SenhaForte123!'))
        self.assertEqual(get_user_model().objects.filter(email='maria@teste.com').count(), 1)

    def test_brigadista_de_outra_brigada_nao_pode_ser_adicionado(self):
        self.client.post(reverse('home'), self._dados_validos(nome='Brigada Norte'))

        response = self.client.post(reverse('home'), self._dados_validos())

        self.assertContains(response, 'já faz parte da brigada &quot;Brigada Norte&quot;')
        self.assertFalse(Brigada.objects.filter(nome='Brigada Centro').exists())

    def test_brigadista_com_cpf_invalido_nao_salva_nada(self):
        response = self.client.post(reverse('home'), self._dados_validos(
            brigadistas=(
                'Maria Silva | maria@teste.com | 529.982.247-25\n'
                'João Pereira | joao@teste.com | 000.000.000-00'
            ),
        ))

        self.assertContains(response, 'Brigadista 2 (João Pereira): informe um CPF válido.')
        self.assertFalse(Brigada.objects.exists())
        self.assertFalse(Perfil.objects.exists())

    def test_email_e_cpf_de_contas_diferentes_sao_rejeitados(self):
        joao = get_user_model().objects.create_user('joao@teste.com', 'joao@teste.com')
        Perfil.objects.create(usuario=joao, nome_completo='João Pereira', cpf='11144477735')

        response = self.client.post(reverse('home'), self._dados_validos(
            brigadistas='Maria Silva | joao@teste.com | 529.982.247-25',
        ))

        self.assertContains(response, 'este e-mail já está cadastrado com outro CPF')
        self.assertFalse(Brigada.objects.exists())

    def test_cpf_existente_com_outro_email_vincula_conta_e_troca_email(self):
        fabio = get_user_model().objects.create_user('antigo@teste.com', 'antigo@teste.com', 'senha123')
        Perfil.objects.create(usuario=fabio, nome_completo='Fabio Teste', cpf='52998224725')

        response = self.client.post(reverse('home'), self._dados_validos(
            brigadistas='Fabio Teste | fabio@teste.com | 529.982.247-25',
        ))

        self.assertEqual(response.status_code, 302)
        fabio.refresh_from_db()
        self.assertEqual((fabio.username, fabio.email), ('fabio@teste.com', 'fabio@teste.com'))
        self.assertEqual(fabio.perfil.brigada, Brigada.objects.get())
        self.assertEqual(get_user_model().objects.filter(perfil__cpf='52998224725').count(), 1)

    def test_cpf_de_conta_protegida_com_outro_email_e_rejeitado(self):
        admin = get_user_model().objects.create_superuser('admin@teste.com', 'admin@teste.com', 'senha123')
        Perfil.objects.create(usuario=admin, nome_completo='Admin', cpf='52998224725')

        response = self.client.post(reverse('home'), self._dados_validos(
            brigadistas='Fabio Teste | fabio@teste.com | 529.982.247-25',
        ))

        self.assertContains(response, 'este CPF pertence a uma conta de administrador ou de responsável por brigada, cujo e-mail não pode ser trocado; informe o e-mail já cadastrado nessa conta')
        admin.refresh_from_db()
        self.assertEqual(admin.email, 'admin@teste.com')

    def test_brigadista_repetido_na_lista_e_rejeitado(self):
        response = self.client.post(reverse('home'), self._dados_validos(
            brigadistas=(
                'Maria Silva | maria@teste.com | 529.982.247-25\n'
                'Maria S. | maria@teste.com | 111.444.777-35'
            ),
        ))

        self.assertContains(response, 'e-mail ou CPF repetido na lista')
        self.assertFalse(Brigada.objects.exists())

    def test_salvar_brigada_registra_quem_criou(self):
        self.client.post(reverse('home'), self._dados_validos())

        self.assertEqual(Brigada.objects.get().criado_por, self.user)


class GerenciamentoBrigadasTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='criador', password='senha123')
        self.outro = user_model.objects.create_user(username='outro', password='senha123')
        self.client.force_login(self.user)
        self.client.post(reverse('home'), {
            'nome': 'Brigada Centro',
            'endereco': 'Rua A, 10',
            'latitude': '-12.97',
            'longitude': '-38.5',
            'brigadistas': (
                'Maria Silva | maria@teste.com | 529.982.247-25 | 71999990000 | 37 | M | 40\n'
                'João Pereira | joao@teste.com | 111.444.777-35'
            ),
        })
        self.brigada = Brigada.objects.get()
        self.brigada_alheia = Brigada.objects.create(nome='Brigada Alheia', endereco='Rua B', criado_por=self.outro)

    def test_lista_exibe_somente_brigadas_do_usuario(self):
        response = self.client.get(reverse('minhas_brigadas'))

        self.assertContains(response, 'Brigada Centro')
        self.assertNotContains(response, 'Brigada Alheia')
        self.assertContains(response, reverse('editar_brigada', args=[self.brigada.pk]))

    def test_lista_requer_autenticacao(self):
        self.client.logout()

        response = self.client.get(reverse('minhas_brigadas'))

        self.assertEqual(response.status_code, 302)

    def test_edicao_exibe_brigadistas_atuais(self):
        response = self.client.get(reverse('editar_brigada', args=[self.brigada.pk]))

        self.assertContains(response, 'Editar brigada')
        self.assertContains(response, 'Maria Silva | maria@teste.com | 52998224725 | 71999990000 | 37 | M | 40')
        self.assertContains(response, 'João Pereira | joao@teste.com | 11144477735')

    def test_edicao_salva_dados_e_exclui_conta_de_quem_saiu_da_lista(self):
        response = self.client.post(reverse('editar_brigada', args=[self.brigada.pk]), {
            'nome': 'Brigada Centro Renomeada',
            'endereco': 'Rua A, 10',
            'latitude': '-12.97',
            'longitude': '-38.5',
            'brigadistas': 'Maria Silva | maria@teste.com | 529.982.247-25 | 71999990000 | 38 | G | 42',
        })

        self.assertRedirects(response, reverse('minhas_brigadas'))
        self.brigada.refresh_from_db()
        self.assertEqual(self.brigada.nome, 'Brigada Centro Renomeada')
        self.assertEqual(self.brigada.criado_por, self.user)
        maria = Perfil.objects.get(cpf='52998224725')
        self.assertEqual((maria.brigada, maria.numero_calcado, maria.tamanho_blusa), (self.brigada, 38, 'G'))
        self.assertFalse(Perfil.objects.filter(cpf='11144477735').exists())
        self.assertFalse(get_user_model().objects.filter(username='joao@teste.com').exists())

    def test_nao_edita_nem_exclui_brigada_de_outro_usuario(self):
        url_editar = reverse('editar_brigada', args=[self.brigada_alheia.pk])
        url_excluir = reverse('excluir_brigada', args=[self.brigada_alheia.pk])

        self.assertEqual(self.client.get(url_editar).status_code, 404)
        self.assertEqual(self.client.post(url_excluir).status_code, 404)
        self.assertTrue(Brigada.objects.filter(pk=self.brigada_alheia.pk).exists())

    def test_exclusao_remove_brigada_e_contas_dos_brigadistas(self):
        response = self.client.post(reverse('excluir_brigada', args=[self.brigada.pk]), follow=True)

        self.assertRedirects(response, reverse('minhas_brigadas'))
        self.assertContains(response, 'Brigada &quot;Brigada Centro&quot; excluída.')
        self.assertFalse(Brigada.objects.filter(pk=self.brigada.pk).exists())
        self.assertFalse(Perfil.objects.exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_exclusao_mantem_conta_de_quem_criou_brigada(self):
        Perfil.objects.create(usuario=self.user, nome_completo='Criador', cpf='02566114595', brigada=self.brigada)

        self.client.post(reverse('excluir_brigada', args=[self.brigada.pk]))

        self.assertTrue(Perfil.objects.filter(usuario=self.user, brigada=None).exists())

    def test_exclusao_exige_post(self):
        response = self.client.get(reverse('excluir_brigada', args=[self.brigada.pk]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Brigada.objects.filter(pk=self.brigada.pk).exists())


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
        brigada = Brigada.objects.create(nome='Brigada Centro', endereco='Rua A, 10')
        Perfil.objects.create(usuario=self.admin, nome_completo='Admin', cpf='52998224725', brigada=brigada)
        for url in (
            reverse('admin:accounts_brigada_change', args=[brigada.pk]),
            reverse('admin:index'),
            reverse('admin:auth_user_change', args=[self.admin.pk]),
            reverse('admin:auth_user_add'),
            reverse('admin:accounts_brigada_changelist'),
            reverse('admin:accounts_perfil_changelist'),
            reverse('admin:accounts_brigada_changelist') + '?q=Maria',
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_exige_staff(self):
        self.client.logout()
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
