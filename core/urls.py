from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from accounts.views import cadastro_usuario, home


def index(request):
    if request.user.is_authenticated:
        return redirect('home')
    return redirect('login')


urlpatterns = [
    path('', index, name='index'),
    path('home/', home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('cadastro/', cadastro_usuario, name='cadastro_usuario'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
