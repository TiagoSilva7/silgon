Projeto SILGON

Aplicacao Flask com banco SQLite local para cadastro e atendimento de pacientes.

Arquivos principais

- `app.py`: servidor Flask principal.
- `portable_server.py`: inicializacao para uso empacotado e abertura automatica do navegador.
- `templates/index.html`: interface principal.
- `static/`: assets do frontend e arquivos PWA.
- `build_portable.bat`: gera pasta portatil com PyInstaller.

Como rodar em desenvolvimento

No terminal, a partir da raiz do workspace:

```powershell
python -m pip install -r SILGON/requirements.txt
python SILGON/app.py
```

Depois abra:

```text
http://127.0.0.1:5000/
```

Atalhos do VS Code

- Task `SILGON: Install requirements`
- Task `SILGON: Run Flask app`
- Task `SILGON: Build portable`
- Launch `SILGON: Flask`
- Launch `SILGON: Portable server`

Teste rapido da API

Com o servidor em execucao:

```powershell
python SILGON/test_post.py
```

Build portatil

```powershell
SILGON\build_portable.bat
```

Saida esperada:

```text
dist\SILGON\
```
