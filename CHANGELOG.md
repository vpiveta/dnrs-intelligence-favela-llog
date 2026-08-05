# Enterprise 1.1.6

- Gráfico principal alterado de Produtos para Categorias de produtos.
- Clique na categoria abre somente os DNRs daquela categoria.
- Comparação semanal usa Categoria no lugar de Produto.
- Mantidas as correções de usuários, PostgreSQL, Sala de Guerra, GEO e Analytics.

# 1.1.0 — Homologação

- Sala de Guerra usa todo o período por padrão.
- Cliente reincidente calculado por base + cliente + endereço normalizado.
- Nomes iguais em endereços diferentes são apresentados para validação, não como reincidência.
- Itens de reincidência e tendências são clicáveis.
- GEO não inventa coordenadas pelo centro da base; somente exatas/validadas ou CEP oficial.
- Geocodificação valida CEP, cidade e UF.
- Gráfico de horário em rosca com percentual.
- Motoristas exibidos como BASE · Nome abreviado no consolidado.
- Período completo disponível em Sala de Guerra e Analytics.

# Changelog

## 0.8.0 Web

- Projeto consolidado em uma única raiz.
- Configuração de produção para Render.
- Compatibilidade com PostgreSQL/Supabase via `DATABASE_URL`.
- Health check `/health`.
- Gunicorn para produção.
- Script de migração SQLite → PostgreSQL.
- Publicação automática pelo GitHub/Render.
- Inicializador local separado da configuração web.
- Controle de acesso por base preservado.
- Versão visível `0.8.0-web`.


## 1.0.0-enterprise
- Migrador Supabase interativo e corrigido.
- Administração → Plataforma com diagnóstico.
- Atualização oficial via GitHub/Render.
- Estrutura de pastas versionada sem dados sensíveis.
- Workflow de verificação no GitHub.

## Enterprise 1.1.3 Final
- Fila de prioridades abre exatamente os DNRs de cada indicador.
- Base, período e tela de origem são preservados.
- Reincidência de cliente usa Base + Cliente + Endereço normalizado.
- Endereço reincidente usa Base + Endereço normalizado.
- Cards da Sala de Guerra também são contextuais.

## 1.1.5 - Senha no cadastro de usuários
- Senha inicial e confirmação no cadastro.
- Hash seguro da senha.
- Troca obrigatória configurável no primeiro acesso.
- Redefinição de senha para usuários existentes.

## 2.0.0-rc1
- Gráficos de categorias e bases convertidos para rosca.
- Comparação automática entre semana atual/anterior ou blocos de quatro semanas.
- Painel de oportunidades para redução de DNR.
- Processamento progressivo dos endereços pendentes no GEO.
- Diagnóstico de carregamento dos pontos do mapa.

## 2.0.0-rc2
- Filtros por dia exato, intervalo de datas e semana, combináveis com base individual ou todas as bases.
- Escolha entre data de entrega e data de abertura do DNR.
- Novo campo data de abertura do DNR reconhecido na importação e atualização de lotes antigos.

## 2.0.0-rc2.3
- Padronização responsiva dos filtros avançados.
- Correção do modal de exclusão de lotes.
- Campos de data, semana, ano, base e ações alinhados ao layout.


## 2.0.0-final-ui
- Filtros padronizados em Dashboard, Analytics, Casos, Sala de Guerra, Inteligência e GEO.
- Remoção do filtro de Base duplicado no GEO.
- Cards de status GEO e diagnóstico quando não existem pontos válidos.
- Layout responsivo e campo de data no tema escuro.
