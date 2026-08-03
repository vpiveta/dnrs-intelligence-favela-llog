# GEO Intelligence — Sprint 6

## Recursos

- Mapa Leaflet/OpenStreetMap em tema escuro.
- Marcadores agrupados por cluster.
- Alternância para mapa de calor.
- Filtros por base, motorista, login utilizado, produto, endereço, CEP, TBR e cliente.
- Abertura direta da investigação pelo ponto no mapa.
- Geocodificação individual com cache no próprio caso.
- Cadastro manual de latitude e longitude quando o serviço automático não localizar.
- Campos preparados para login próprio e proprietário do login.

## Preservação do banco

Ao abrir esta versão sobre um banco antigo, o DNR Intelligence verifica as colunas ausentes. Antes de alterar o SQLite, cria uma cópia em `backups/` e aplica somente as novas colunas.

Antes de excluir um lote importado, também é criado um backup automático.

## Observação sobre o mapa

Os mapas e a geocodificação usam serviços públicos do OpenStreetMap. O computador precisa de internet para carregar os blocos do mapa e localizar novos endereços. As coordenadas já salvas continuam no banco e não precisam ser pesquisadas novamente.

## Localização em lote
Use **Localizar próximos 20** para processar os endereços gradualmente. O limite reduz bloqueios do serviço público de mapas. Quando a porta exata não for encontrada, o sistema pode usar a coordenada aproximada do CEP e marcar o registro como `CEP_APROXIMADO`.
