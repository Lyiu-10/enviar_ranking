# Ranking de gastos por evento

Uma TV mostra os 10 clientes que mais gastaram no evento, sem mostrar valores. O caixa lança os pedidos pelo notebook.

## Como usar

1. Instale o [Python 3](https://www.python.org/downloads/).
2. Dê dois cliques em `INICIAR.bat`. O caixa abre sozinho em `http://localhost:8000/admin`.
3. Na TV, abra o endereço que aparece na janela, no formato `http://<ip-do-notebook>:8000/`.

Os dados ficam em `dados.json`, e o programa guarda uma cópia por dia em `backups/`. Nenhum dos dois vai para o repositório. Para começar um evento novo, use **⚙ Configurações → Novo evento**.

Para conferir o programa: `python server.py --teste`
