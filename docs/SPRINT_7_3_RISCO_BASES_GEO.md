# Sprint 7.3 — Risco por valor, bases individuais e GEO resiliente

## Faixas oficiais
- Crítico: R$ 1.000,00 ou mais.
- Alto: R$ 500,00 a R$ 999,99.
- Médio: R$ 100,00 a R$ 499,99.
- Baixo: abaixo de R$ 100,00.

Recorrência de motorista, login, cliente e endereço permanece como análise operacional, mas não altera a faixa oficial de risco do caso.

## Geocodificação
O DNR Intelligence respeita o limite do serviço público Nominatim, controla o intervalo entre consultas, pausa ao receber HTTP 429 e utiliza CEP/coordenadas aproximadas para manter todos os casos visíveis no mapa.

## Bases
A tela Analytics permite filtrar uma base individualmente e comparar todas as bases por volume, valor, vencimentos, resolução e distribuição de risco.
