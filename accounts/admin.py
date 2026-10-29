from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Brigada, Perfil

admin.site.site_header = 'Cadastro Estadual de Brigadas'
admin.site.site_title = 'Administração'
admin.site.index_title = 'Administração do sistema'


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name = 'Perfil'
    verbose_name_plural = 'Perfil'
    fields = ('nome_completo', 'cpf', 'brigada', 'telefone', 'numero_calcado', 'tamanho_blusa', 'tamanho_calca')


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'cpf', 'usuario', 'brigada')
    list_filter = ('brigada',)
    search_fields = ('nome_completo', 'cpf', 'usuario__email', 'usuario__username')
    raw_id_fields = ('usuario', 'brigada')


class BrigadistaInline(admin.TabularInline):
    model = Perfil
    fk_name = 'brigada'
    extra = 0
    verbose_name = 'Brigadista'
    verbose_name_plural = 'Brigadistas'
    fields = ('nome_completo', 'cpf', 'usuario', 'telefone', 'numero_calcado', 'tamanho_blusa', 'tamanho_calca')
    readonly_fields = ('nome_completo', 'cpf', 'usuario')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    inlines = (PerfilInline,)
    list_display = ('username', 'nome_completo', 'cpf', 'is_active', 'is_staff', 'last_login', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'perfil__nome_completo', 'perfil__cpf')
    ordering = ('-date_joined',)
    list_select_related = ('perfil',)

    @admin.display(description='Nome completo', ordering='perfil__nome_completo')
    def nome_completo(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return perfil.nome_completo if perfil else obj.get_full_name() or '—'

    @admin.display(description='CPF', ordering='perfil__cpf')
    def cpf(self, obj):
        perfil = getattr(obj, 'perfil', None)
        if not perfil:
            return '—'
        c = perfil.cpf
        return f'{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}'


@admin.register(Brigada)
class BrigadaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'municipio', 'endereco', 'created_at')
    list_filter = ('municipio',)
    search_fields = ('nome', 'municipio', 'endereco', 'cep', 'brigadistas__nome_completo', 'brigadistas__cpf')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    inlines = (BrigadistaInline,)
