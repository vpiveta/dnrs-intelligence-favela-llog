# Data Engine 0.6.5

O importador oficial reconhece CSV separado por ponto e vírgula e XLSX.

## Cabeçalhos oficiais
- TBR
- Data de entrega (data e hora completas)
- data da entrega (data)
- hora da entrega (hora)
- Nome do agente de entrega (motorista)
- Login utilizado (quando disponível)
- Endereço
- CEP mapa
- Cliente
- Valor
- Semana

Antes da gravação, o sistema mostra prévia, mapeamento e qualidade estimada. A confirmação cria o lote e os casos. Novas colunas são adicionadas ao SQLite por migração automática, com backup anterior.
