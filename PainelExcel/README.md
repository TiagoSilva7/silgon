PainelExcel
===========
Protótipo simples para fazer upload de um arquivo Excel/CSV e visualizar os dados em um dashboard.

Requisitos
- Python 3.8+
- Virtualenv (recomendado)

Instalação rápida

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Executar

```powershell
python app.py
# Abrir http://127.0.0.1:5000/
```

Atalho (abre Chrome automaticamente)

```powershell
# PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File run_server.ps1

# Ou no Windows Explorer/Command Prompt
run_server.bat
```

Fluxo
- Faça upload do arquivo via página inicial.
- O servidor converte para `data/data.csv` e redireciona para o dashboard.
- O dashboard busca `/data` em JSON e mostra tabela + um gráfico simples.

Notas
- Suporta XLS/XLSX/CSV.
- Você pode estender o mapeamento de colunas no `app.py` antes de salvar.
