#!/usr/bin/env python3
"""
Consulta a REST API (versão mais recente) do Strategy para retornar todas as
configurações do usuário informado (por login). Escreve JSON completo no arquivo
`user_<login>_details.json` na mesma pasta.

Edite as constantes abaixo se necessário: `BASE_URL`, `API_USER`, `API_PASS`, `TARGET_LOGIN`.

Uso:
  python get_user_details.py
"""
import json
import os
from typing import Optional

import requests

# --- CONFIGURAÇÃO ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
API_USER = "31071655817"
API_PASS = "Tera!7777"
TARGET_LOGIN = "11620109751"


def auth_get_token(session: requests.Session) -> Optional[str]:
    try:
        r = session.post(f"{BASE_URL.rstrip('/')}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=15)
        if r.status_code in (200, 204):
            return r.headers.get('X-MSTR-AuthToken') or r.headers.get('x-mstr-authtoken')
        print(f"Falha no login: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Erro na autenticação: {e}")
    return None


def find_user(session: requests.Session, login_value: str) -> Optional[dict]:
    # 1) tentar searchPattern
    try:
        r = session.get(f"{BASE_URL.rstrip('/')}/users", params={"searchPattern": login_value}, timeout=12)
        if r.status_code == 200:
            data = r.json()
            items = data if isinstance(data, list) else data.get('users') or data.get('items') or []
            for u in items:
                # checar campos que representam o login/abreviação
                if str(u.get('abbreviation') or u.get('login') or u.get('username') or u.get('name') or '').strip().lower() == login_value.strip().lower():
                    return u
            if items:
                return items[0]

        # 2) tentar param 'search'
        r2 = session.get(f"{BASE_URL.rstrip('/')}/users", params={"search": login_value}, timeout=10)
        if r2.status_code == 200:
            data2 = r2.json()
            items2 = data2 if isinstance(data2, list) else data2.get('users') or data2.get('items') or []
            for u in items2:
                if str(u.get('abbreviation') or u.get('login') or u.get('username') or u.get('name') or '').strip().lower() == login_value.strip().lower():
                    return u
            if items2:
                return items2[0]

    except Exception as e:
        print(f"Erro buscando usuário: {e}")
    return None


def fetch_user_details(session: requests.Session, user_id: str) -> Optional[dict]:
    # solicitar com campos que trazem memberships, addresses e demais propriedades
    fields = 'id,name,abbreviation,emailAddress,enabled,status,createdOn,lastLogin,memberships,addresses,properties,roles,preferences'
    try:
        r = session.get(f"{BASE_URL.rstrip('/')}/users/{user_id}", params={'fields': fields}, timeout=12)
        if r.status_code == 200:
            return r.json()
        # fallback: tentar sem fields
        r2 = session.get(f"{BASE_URL.rstrip('/')}/users/{user_id}", timeout=12)
        if r2.status_code == 200:
            return r2.json()
        print(f"GET /users/{user_id} retornou {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Erro obtendo detalhes do usuário: {e}")
    return None


def resolve_group_names(session: requests.Session, memberships) -> list:
    names = []
    if not memberships:
        return names
    for m in memberships:
        if isinstance(m, dict):
            # se já tem nome, usa
            name = m.get('name') or m.get('groupName') or m.get('displayName')
            gid = m.get('id') or m.get('groupId')
            if name:
                names.append(str(name).strip())
            elif gid:
                try:
                    gr = session.get(f"{BASE_URL.rstrip('/')}/usergroups/{gid}", timeout=8)
                    if gr.status_code == 200:
                        gobj = gr.json()
                        gname = gobj.get('name') or gobj.get('displayName')
                        if gname:
                            names.append(str(gname).strip())
                except Exception:
                    pass
        else:
            # membership pode ser string ou id
            s = str(m).strip()
            if s.isalnum():
                # pode ser id -> tentar buscar
                try:
                    gr = session.get(f"{BASE_URL.rstrip('/')}/usergroups/{s}", timeout=8)
                    if gr.status_code == 200:
                        gobj = gr.json()
                        gname = gobj.get('name') or gobj.get('displayName')
                        if gname:
                            names.append(str(gname).strip())
                            continue
                except Exception:
                    pass
            # se não conseguiu resolver, guarda o literal
            if s:
                names.append(s)
    return names


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    session = requests.Session()
    token = auth_get_token(session)
    if not token:
        print("Autenticação falhou; verifique as credenciais no script.")
        return
    session.headers.update({'X-MSTR-AuthToken': token, 'Accept': 'application/json'})

    print(f"Procurando usuário: {TARGET_LOGIN}")
    user = find_user(session, TARGET_LOGIN)
    if not user:
        print("Usuário não encontrado pela API de busca.")
        return

    user_id = user.get('id') or user.get('userId') or ''
    print(f"Encontrado: id={user_id} name={user.get('name')} abbreviation={user.get('abbreviation')}")

    details = fetch_user_details(session, user_id) if user_id else user
    if not details:
        print("Não foi possível obter detalhes do usuário.")
        return

    # tentar resolver nomes dos grupos (memberships)
    memberships = details.get('memberships') or details.get('groups') or details.get('memberOf') or []
    group_names = resolve_group_names(session, memberships)
    details['_resolved_group_names'] = group_names

    out_file = os.path.join(script_dir, f"user_{TARGET_LOGIN}_details.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(details, f, indent=2, ensure_ascii=False)

    print(f"Detalhes salvos em: {out_file}")
    print(json.dumps(details, indent=2, ensure_ascii=False))

    # logout
    try:
        session.post(f"{BASE_URL.rstrip('/')}/auth/logout", headers={'X-MSTR-AuthToken': token}, timeout=5)
    except Exception:
        pass


if __name__ == '__main__':
    main()
