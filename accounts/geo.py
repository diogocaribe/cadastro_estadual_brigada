"""Limite territorial da Bahia (malha do IBGE) e teste de ponto no polígono.

O mesmo arquivo é servido ao mapa da página inicial, para que a validação
do navegador e a do servidor usem exatamente o mesmo contorno."""

import json
from functools import lru_cache
from pathlib import Path

BAHIA_GEOJSON = Path(__file__).resolve().parent / 'data' / 'bahia.geojson'


@lru_cache(maxsize=1)
def _poligonos_bahia():
    with BAHIA_GEOJSON.open(encoding='utf-8') as arquivo:
        dados = json.load(arquivo)

    poligonos = []
    for feicao in dados['features']:
        geometria = feicao['geometry']
        if geometria['type'] == 'Polygon':
            poligonos.append(geometria['coordinates'])
        elif geometria['type'] == 'MultiPolygon':
            poligonos.extend(geometria['coordinates'])
    return poligonos


def _ponto_no_anel(x, y, anel):
    dentro = False
    j = len(anel) - 1
    for i in range(len(anel)):
        xi, yi = anel[i][:2]
        xj, yj = anel[j][:2]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def ponto_na_bahia(latitude, longitude):
    """Indica se a coordenada (graus decimais, WGS 84) está dentro da Bahia."""
    return any(
        _ponto_no_anel(longitude, latitude, aneis[0])
        and not any(_ponto_no_anel(longitude, latitude, buraco) for buraco in aneis[1:])
        for aneis in _poligonos_bahia()
    )
