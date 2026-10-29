from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import redirect
from django.urls import path

from accounts.forms import LoginForm
from accounts.views import cadastro_usuario, editar_brigada, excluir_brigada, home, limite_bahia, minhas_brigadas


def index(request):
    if request.user.is_authenticated:
        return redirect('home')
    return redirect('login')


urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('home/', home, name='home'),
    path('brigadas/', minhas_brigadas, name='minhas_brigadas'),
    path('brigadas/<int:pk>/editar/', editar_brigada, name='editar_brigada'),
    path('brigadas/<int:pk>/excluir/', excluir_brigada, name='excluir_brigada'),
    path('geo/bahia.geojson', limite_bahia, name='limite_bahia'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('cadastro/', cadastro_usuario, name='cadastro_usuario'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

# Em desenvolvimento o gunicorn não serve arquivos estáticos (ex.: CSS do admin).
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
