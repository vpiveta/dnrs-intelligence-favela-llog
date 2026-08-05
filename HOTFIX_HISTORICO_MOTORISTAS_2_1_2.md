# Hotfix 2.1.2 — Histórico de Motoristas

Correção do erro 500 ao abrir `/historico-motoristas/`.

## Causa
No template Jinja, `row.values` era interpretado como o método nativo `dict.values`, e não como a lista armazenada na chave `values`. Por isso o Jinja tentou iterar um método e gerou:

`TypeError: builtin_function_or_method object is not iterable`

## Correção
O acesso foi alterado para `row['values']`, eliminando a ambiguidade sem alterar banco, filtros, gráficos ou dados existentes.
