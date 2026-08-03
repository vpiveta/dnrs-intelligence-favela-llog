# Atualização de planilhas existentes e GEO

- Use **Atualizar planilhas já importadas** no histórico para reaproveitar os arquivos originais salvos em `uploads`.
- O processo atualiza motorista, login, data, hora, semana, valor, CEP e demais campos pelo TBR, sem criar duplicados.
- Se o arquivo original não estiver mais em `uploads`, será necessário reenviar a planilha.
- O modelo oficial está em `modelos/Modelo_Oficial_DNR_Intelligence.xlsx` e também pode ser baixado pela tela de Importações.
- O GEO tenta localizar endereço completo, versão simplificada, dados oficiais do ViaCEP e, por último, posição aproximada pelo CEP.
- A tela GEO possui clusters, heatmap, rastreamento por CEP e abertura direta do mapa a partir do endereço do caso.
