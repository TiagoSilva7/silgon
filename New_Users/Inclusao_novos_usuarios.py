import pandas as pd
import requests
import os
from datetime import datetime
import unicodedata

# Configurações
    #MSTR_URL = "http://10.14.203.158:8080/SEFADEVLIB/api"
MSTR_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
ADMIN_USER = "31071655817"
ADMIN_PASS = "SENHA"
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "Lista_Oficial_att.xlsx")
LOG_PATH = os.path.join(os.path.dirname(__file__), "log_criacao_usuarios_prod.txt")

def log_result(message):
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now().isoformat()} - {message}\n")

# 1. Autenticação
auth_response = requests.post(
    f"{MSTR_URL}/auth/login",
    json={"username": ADMIN_USER, "password": ADMIN_PASS}
)
auth_token = auth_response.headers.get("X-MSTR-AuthToken")
session_id = auth_response.cookies.get("JSESSIONID")
headers = {
    "X-MSTR-AuthToken": auth_token,
    "Content-Type": "application/json",
    "Accept": "application/json"
}
cookies = {"JSESSIONID": session_id}

# 2. Ler Excel (normaliza nomes de colunas)
def _normalize_col(name: str) -> str:
    name = str(name).strip().lower().replace(" ", "_")
    return ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )

df = pd.read_excel(EXCEL_PATH)
df.rename(columns=lambda c: _normalize_col(c), inplace=True)
print("Colunas encontradas:", list(df.columns))

# 3. Criar usuários
def _get_field(row, candidates):
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return row[c]
    return None

for _, row in df.iterrows():
    nome = _get_field(row, ["nome", "name", "full_name", "fullname"]) 
    login = _get_field(row, ["login", "username", "user"]) 
    email = _get_field(row, ["email", "email_address", "emailaddress", "e_mail"]) 

    if not nome or not login:
        msg = f"Pular linha: colunas obrigatórias ausentes (nome: {nome}, login: {login})"
        print(msg)
        log_result(f"AVISO: {msg}")
        continue

    if email and "@" not in str(email):
        email = f"{email}@dominio.com"

    payload = {
        "fullName": nome,
        "username": login,
        "password": "Sefaagaa2026",
        "emailAddress": email if email else "",
        "enabled": True
    }
    resp = requests.post(
        f"{MSTR_URL}/users",
        json=payload,
        headers=headers,
        cookies=cookies
    )
    if resp.status_code == 201:
        print(f"Usuário {row['login']} criado com sucesso.")
        log_result(f"SUCESSO: Usuário {row['login']} criado.")
    else:
        print(f"Erro ao criar {row['login']}: {resp.text}")
        log_result(f"ERRO: Usuário {row['login']} - {resp.text}")

# 4. Logout
requests.post(f"{MSTR_URL}/auth/logout", headers=headers, cookies=cookies)
