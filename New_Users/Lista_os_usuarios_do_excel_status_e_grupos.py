#!/usr/bin/env python3
"""
Lê logins do Excel (primeira coluna) e exporta um arquivo Excel com as colunas:
  - name
  - id
  - abbreviation
  - enabled
  - _resolved_group_names

Configurar `BASE_URL`, `API_USER`, `API_PASS` e `EXCEL_FILENAME` abaixo se necessário.
"""
import os
import json
from typing import List, Optional

import requests
from collections import Counter
import re
import unicodedata
from openpyxl import load_workbook, Workbook

# --- CONFIGURAÇÃO ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
API_USER = "31071655817"
API_PASS = "Tera!7777"
EXCEL_FILENAME = "Lista_Oficial_att_new_groups.xlsx"  # arquivo na mesma pasta
OUTPUT_FILENAME = "users_summary.xlsx"


def auth_get_token(session: requests.Session) -> Optional[str]:
    try:
        r = session.post(f"{BASE_URL.rstrip('/')}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=15)
        if r.status_code in (200, 204):
            return r.headers.get('X-MSTR-AuthToken') or r.headers.get('x-mstr-authtoken')
        print(f"Falha no login: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Erro na autenticação: {e}")
    return None


def bool_enabled(raw_status) -> bool:
    """Retorna True/False a partir de diversos formatos de status."""
    if raw_status is None:
        return False
    if isinstance(raw_status, bool):
        return raw_status
    s = str(raw_status).strip().lower()
    if s in ('enabled', 'enable', 'active', 'true', '1', 'ok'):
        return True
    if s in ('disabled', 'disable', 'inactive', 'false', '0'):
        return False
    # fallback: False
    return False


def read_logins(path: str) -> List[str]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    out = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row:
            continue
        val = row[0]
        if val is None:
            continue
        s = str(val).strip()
        if s:
            out.append(s)
    return out


def normalize_login_value(s: str) -> str:
    """Normalize login string: remove unicode oddities and return digits-only when possible."""
    if s is None:
        return ''
    s = str(s)
    s = unicodedata.normalize('NFKC', s)
    s = s.replace('\u00A0', ' ').replace('\u200B', '')
    s = s.strip()
    digits = re.sub(r"\D", "", s)
    # Remove leading zeros coming from Excel (e.g., '05492650904' -> '5492650904')
    if digits:
        stripped = digits.lstrip('0')
        # if all zeros, keep a single '0'
        return stripped if stripped else '0'
    return s


def find_user(session: requests.Session, login_value: str) -> Optional[dict]:
    """Busca usuário mas só retorna quando encontra correspondência exata no campo de login/abbreviation.
    Não faz fallback para o primeiro item (evita matches incorretos)."""
    try:
        target = normalize_login_value(login_value)
        # tentativa 1: searchPattern — use normalized target (no leading zeros)
        r = session.get(f"{BASE_URL.rstrip('/')}/users", params={"searchPattern": target}, timeout=12)
        if r.status_code == 200:
            data = r.json()
            items = data if isinstance(data, list) else data.get('users') or data.get('items') or []
            for u in items:
                cand = str(u.get('abbreviation') or u.get('login') or u.get('username') or '').strip()
                if normalize_login_value(cand) == target:
                    return u

        # tentativa 2: param 'search' — use normalized target
        r2 = session.get(f"{BASE_URL.rstrip('/')}/users", params={"search": target}, timeout=10)
        if r2.status_code == 200:
            data2 = r2.json()
            items2 = data2 if isinstance(data2, list) else data2.get('users') or data2.get('items') or []
            for u in items2:
                cand = str(u.get('abbreviation') or u.get('login') or u.get('username') or '').strip()
                if normalize_login_value(cand) == target:
                    return u

    except Exception as e:
        print(f"Erro buscando usuário {login_value}: {e}")
    return None


def fetch_details(session: requests.Session, user_id: str) -> Optional[dict]:
    try:
        fields = 'id,name,abbreviation,enabled,memberships'
        r = session.get(f"{BASE_URL.rstrip('/')}/users/{user_id}", params={'fields': fields}, timeout=12)
        if r.status_code == 200:
            return r.json()
        r2 = session.get(f"{BASE_URL.rstrip('/')}/users/{user_id}", timeout=12)
        if r2.status_code == 200:
            return r2.json()
    except Exception as e:
        print(f"Erro fetch details {user_id}: {e}")
    return None


def resolve_group_names(session: requests.Session, memberships) -> List[str]:
    names = []
    if not memberships:
        return names
    for m in memberships:
        if isinstance(m, dict):
            name = m.get('name') or m.get('groupName') or m.get('displayName')
            gid = m.get('id') or m.get('groupId')
            if name:
                names.append(str(name).strip())
            elif gid:
                try:
                    gr = session.get(f"{BASE_URL.rstrip('/')}/usergroups/{gid}", timeout=8)
                    if gr.status_code == 200:
                        g = gr.json()
                        gname = g.get('name') or g.get('displayName')
                        if gname:
                            names.append(str(gname).strip())
                except Exception:
                    pass
        else:
            s = str(m).strip()
            if s.isalnum():
                try:
                    gr = session.get(f"{BASE_URL.rstrip('/')}/usergroups/{s}", timeout=8)
                    if gr.status_code == 200:
                        g = gr.json()
                        gname = g.get('name') or g.get('displayName')
                        if gname:
                            names.append(str(gname).strip())
                            continue
                except Exception:
                    pass
            if s:
                names.append(s)
    return names


def write_excel(path: str, rows: List[dict]):
    wb = Workbook()
    ws = wb.active
    # ordem solicitada: abbreviation, name, enabled, _resolved_group_names
    headers = ['abbreviation', 'name', 'enabled', '_resolved_group_names']
    ws.append(headers)
    for r in rows:
        ws.append([r.get('abbreviation', ''), r.get('name', ''), r.get('enabled', ''), r.get('_resolved_group_names', '')])
    wb.save(path)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(script_dir, EXCEL_FILENAME)
    if not os.path.exists(excel_path):
        print(f"Arquivo Excel não encontrado: {excel_path}")
        return

    logins = read_logins(excel_path)
    if not logins:
        print("Nenhum login encontrado no Excel.")
        return

    # Normalizar e contar ocorrências para diagnosticar duplicatas
    normed = [normalize_login_value(l) for l in logins if l is not None and str(l).strip()]
    counts = Counter(normed)
    duplicates = [k for k, v in counts.items() if v > 1]
    if duplicates:
        dup_path = os.path.join(script_dir, 'duplicate_logins.txt')
        with open(dup_path, 'w', encoding='utf-8') as df:
            df.write('login,count\n')
            for k in duplicates:
                df.write(f"{k},{counts[k]}\n")
        print(f"AVISO: foram encontradas {len(duplicates)} logins duplicados no Excel. Lista gravada em: {dup_path}")

    # Remover duplicatas preservando a ordem (garante que cada login apareça apenas uma vez)
    seen = set()
    unique_logins = []
    for l in normed:
        if l in seen:
            continue
        seen.add(l)
        unique_logins.append(l)

    session = requests.Session()
    token = auth_get_token(session)
    if not token:
        print("Falha na autenticação")
        return
    session.headers.update({'X-MSTR-AuthToken': token, 'Accept': 'application/json'})

    rows = []
    for login in unique_logins:
        user = find_user(session, login)
        if not user:
            rows.append({'name': '', 'id': '', 'abbreviation': login, 'enabled': '', '_resolved_group_names': ''})
            print(f"{login}: NÃO encontrado")
            continue
        user_id = user.get('id') or user.get('userId') or ''
        details = fetch_details(session, user_id) if user_id else user
        name = details.get('name') or ''
        abbrev = details.get('abbreviation') or details.get('abbreviation') or login
        raw_enabled = None
        if 'enabled' in details:
            raw_enabled = details.get('enabled')
        else:
            raw_enabled = details.get('status') or details.get('userStatus')
        enabled_bool = bool_enabled(raw_enabled)
        memberships = details.get('memberships') or details.get('groups') or []
        group_names = resolve_group_names(session, memberships)
        rows.append({'name': name, 'abbreviation': abbrev, 'enabled': enabled_bool, '_resolved_group_names': ';'.join(group_names)})
        print(f"{abbrev}: name={name} enabled={enabled_bool} groups={';'.join(group_names)}")

    out_path = os.path.join(script_dir, OUTPUT_FILENAME)
    write_excel(out_path, rows)
    print(f"Exportado para: {out_path}")

    # Validação: garantir que cada login único do Excel tenha uma linha no arquivo de saída
    expected = len(unique_logins)
    written = len(rows)
    print(f"Processados (únicos): {expected} — Linhas exportadas: {written}")
    if written != expected:
        exported_abbrevs = set(str(r.get('abbreviation', '')).strip() for r in rows)
        missing = [l for l in unique_logins if l not in exported_abbrevs]
        if missing:
            print(f"AVISO: {len(missing)} logins não foram exportados: {missing[:10]}{('...' if len(missing)>10 else '')}")
        else:
            print("AVISO: diferença no número de linhas, mas não foi possível identificar logins faltantes")

    try:
        session.post(f"{BASE_URL.rstrip('/')}/auth/logout", headers={'X-MSTR-AuthToken': token}, timeout=5)
    except Exception:
        pass


if __name__ == '__main__':
    main()
