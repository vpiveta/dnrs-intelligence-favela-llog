# Sprint 7.2 — Automação, Criticidade, SLA e Cobertura do Mapa

## Criticidade automática
Um caso é classificado como crítico quando atender a pelo menos um critério:

- regra anterior substituída na Sprint 7.3 pela classificação exclusiva por faixas de valor;
- motorista com maior quantidade de DNR no período/base;
- login utilizado com maior quantidade de DNR no período/base;
- endereço com maior quantidade de DNR no período/base.

Empates no primeiro lugar são considerados. Rankings com apenas uma ocorrência não geram criticidade por recorrência.

## SLA automático
O prazo é fixado em três dias após o upload da planilha. Casos cadastrados manualmente usam três dias após a criação. O sistema identifica automaticamente os casos vencidos.

## Cobertura do mapa
Todos os casos com endereço aparecem no mapa:

1. coordenada exata salva;
2. posição aproximada pelo CEP;
3. posição aproximada pelo CEP4;
4. centro conhecido da base;
5. posição provisória da operação.

Pontos aproximados são exibidos em amarelo e continuam na fila de geocodificação para obtenção da posição exata.
