from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from .forms import BrigadaForm, CadastroUsuarioForm
from .geo import BAHIA_GEOJSON
from .models import Brigada, retirar_da_brigada


@cache_control(public=True, max_age=86400)
def limite_bahia(request):
    return FileResponse(BAHIA_GEOJSON.open('rb'), content_type='application/geo+json')


@login_required
def home(request):
    if request.method == 'POST':
        form = BrigadaForm(request.POST)
        form.instance.criado_por = request.user
        if form.is_valid():
            brigada = form.save()
            messages.success(request, f'Brigada "{brigada.nome}" cadastrada com sucesso.')
            return redirect('home')
    else:
        form = BrigadaForm()

    return render(request, 'accounts/home.html', {'form': form})


@login_required
def minhas_brigadas(request):
    brigadas = (
        Brigada.objects.filter(criado_por=request.user)
        .annotate(total_brigadistas=Count('brigadistas'))
    )
    return render(request, 'accounts/minhas_brigadas.html', {'brigadas': brigadas})


@login_required
def editar_brigada(request, pk):
    brigada = get_object_or_404(Brigada, pk=pk, criado_por=request.user)
    if request.method == 'POST':
        form = BrigadaForm(request.POST, instance=brigada)
        if form.is_valid():
            brigada = form.save()
            messages.success(request, f'Brigada "{brigada.nome}" atualizada com sucesso.')
            return redirect('minhas_brigadas')
    else:
        form = BrigadaForm(instance=brigada)

    return render(request, 'accounts/home.html', {'form': form, 'brigada': brigada})


@login_required
@require_POST
def excluir_brigada(request, pk):
    brigada = get_object_or_404(Brigada, pk=pk, criado_por=request.user)
    nome = brigada.nome
    with transaction.atomic():
        retirar_da_brigada(brigada.brigadistas.all())
        brigada.delete()
    messages.success(request, f'Brigada "{nome}" excluída.')
    return redirect('minhas_brigadas')


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
