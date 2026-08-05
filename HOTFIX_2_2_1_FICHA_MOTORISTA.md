# Enterprise 2.2.1 — Hotfix da ficha do motorista

- Corrige o erro 500 ao abrir a ficha completa do motorista.
- O template chamava o endpoint inexistente `cases.detail`; o endpoint correto é `cases.detalhe`.
- Mantém TBR clicável e botão Abrir funcionando.
- Adiciona fallback para tratativas cujo usuário tenha sido removido.
- Nenhuma alteração de banco ou migração é necessária.
