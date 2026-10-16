from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import BrigadaForm, CadastroUsuarioForm


@login_required
def home(request):
    if request.method == 'POST':
        form = BrigadaForm(request.POST)
        if form.is_valid():
            brigada = form.save()
            messages.success(request, f'Brigada "{brigada.nome}" cadastrada com sucesso.')
            return redirect('home')
    else:
        form = BrigadaForm()

    return render(request, 'accounts/home.html', {'form': form})


def cadastro_usuario(request):
    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CadastroUsuarioForm()

    return render(request, 'accounts/cadastro.html', {'form': form})
