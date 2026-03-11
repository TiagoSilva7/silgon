"""
assign_users_to_groups.py

Lê o arquivo NOVOS_USUARIOS.xlsx e adiciona cada usuário (por login)
a um ou mais grupos listados na planilha.

Planilha esperada:
- coluna `login` (ou `username`) com o login/abbreviation do usuário
- coluna `groups` ou `grupos` com nomes de grupos separados por `;`
  Exemplo: "200 - novos usuarios; 405 - alteracoes do bi"

O script busca IDs de usuários e grupos via REST API do MicroStrategy
antes de executar os PATCHs de adição.

NÃO executa o script automaticamente — apenas cria o arquivo.
"""

import os
import requests
import pandas as pd
from datetime import datetime
import logging
import unicodedata

# Configurações (ajuste conforme necessário)
MSTR_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
ADMIN_USER = os.environ.get("MSTR_ADMIN_USER", "31071655817")
ADMIN_PASS = os.environ.get("MSTR_ADMIN_PASS", "Tera!7777")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "Lista_Oficial_att_groups_405.xlsx")
LOG_PATH = os.path.join(os.path.dirname(__file__), "log_criacao_usuarios_assign.log")

# Logging simples
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename=LOG_PATH)


def log_result(msg):
    logging.info(msg)
    print(msg)


def main():
    session = requests.Session()

    # 1) Autenticar
    try:
        auth_resp = session.post(f"{MSTR_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=30)
        auth_resp.raise_for_status()
    except Exception as e:
        log_result(f"ERRO: Falha na autenticação: {e}")
        return

    auth_token = auth_resp.headers.get("X-MSTR-AuthToken") or auth_resp.headers.get('x-mstr-authtoken')
    if not auth_token:
        log_result("ERRO: Token de autenticação não retornado.")
        return

    # Usar session.headers para preservar token e cookies nas próximas chamadas
    session.headers.update({"X-MSTR-AuthToken": auth_token, "Accept": "application/json", "Content-Type": "application/json"})

    # 2) Buscar todos os grupos (id,name)
    try:
        grp_resp = session.get(f"{MSTR_URL}/usergroups", params={"limit": "-1", "fields": "id,name"}, timeout=30)
        grp_resp.raise_for_status()
        groups = grp_resp.json()
    except Exception as e:
        log_result(f"ERRO: Não foi possível obter lista de grupos: {e}")
        groups = []

    # Mapas utilitários: nome normalizado -> id e prefixo (antes do '-') -> id (primeiro encontrado)
    def _norm(s: str) -> str:
        if s is None:
            return ""
        s = str(s)
        # remover aspas e caracteres problemáticos
        s = s.replace('"', '').replace("'", '').replace('`', '')
        # normalizar acentuação
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        # reduzir espaços múltiplos e padronizar
        s = ' '.join(s.split()).strip().lower()
        return s

    groups_by_name = { _norm(g.get("name")): g.get("id") for g in groups }
    groups_by_prefix = {}
    for g in groups:
        name = g.get("name", "")
        prefix = name.split("-")[0].strip() if "-" in name else name.strip()
        npre = _norm(prefix)
        if npre and npre not in groups_by_prefix:
            groups_by_prefix[npre] = g.get("id")

    log_result(f"INFO: {len(groups)} grupos carregados do MicroStrategy")

    # 3) Buscar todos os usuários (id,abbreviation)
    try:
        users_resp = session.get(f"{MSTR_URL}/users", params={"limit": "-1", "fields": "id,abbreviation"}, timeout=30)
        users_resp.raise_for_status()
        users = users_resp.json()
    except Exception as e:
        log_result(f"ERRO: Não foi possível obter lista de usuários: {e}")
        users = []

    # mapear por abbreviation normalizada (retira zeros à esquerda e espaços)
    def _norm_abbrev(s: str) -> str:
        if s is None:
            return ''
        s = str(s).strip()
        s = unicodedata.normalize('NFKC', s)
        digits = ''.join(ch for ch in s if ch.isdigit())
        if digits:
            stripped = digits.lstrip('0')
            return stripped if stripped else '0'
        return s.lower()

    users_map = { _norm_abbrev(u.get("abbreviation")): str(u.get("id")) for u in users }
    log_result(f"INFO: {len(users)} usuários carregados do MicroStrategy")

    # 4) Ler Excel
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception as e:
        log_result(f"ERRO: Falha ao ler {EXCEL_PATH}: {e}")
        return

    # normalizar colunas (remove acentos, espaços e deixa minúsculas)
    def _normalize_col(name: str) -> str:
        name = str(name).strip().lower().replace(" ", "_")
        return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')

    df.rename(columns=lambda c: _normalize_col(c), inplace=True)
    log_result(f"INFO: Colunas do Excel: {list(df.columns)}")

    # 5) Iterar pelas linhas e adicionar aos grupos
    def _get_field(row, candidates):
        for c in candidates:
            if c in row and pd.notna(row.get(c)):
                return str(row.get(c)).strip()
        return None

    results = []

    for idx, row in df.iterrows():
        login_raw = _get_field(row, ["login", "username", "abbreviation", "user"])
        if not login_raw:
            log_result(f"AVISO: Linha {idx+2} sem coluna 'login'/'username' — pulando")
            continue

        # normalizar login: remover zeros à esquerda antes de comparar com abbreviation
        login_norm = _norm_abbrev(login_raw)
        user_id = users_map.get(login_norm)
        if not user_id:
            log_result(f"ERRO: Usuário com login '{login_raw}' (normalizado: '{login_norm}') não encontrado no MicroStrategy — verifique abreviação")
            continue

        # obter a célula de grupos
        groups_cell = _get_field(row, ["groups", "grupos", "group", "group_name", "groupname"])

        if not groups_cell:
            log_result(f"AVISO: Nenhum grupo informado para usuário {login_raw} — pulando")
            continue

        # separar por ';'
        target_groups = [g.strip() for g in str(groups_cell).split(";") if g.strip()]

        for grp_text in target_groups:
            # normalizar e tentar correspondência flexível
            ngr = _norm(grp_text)
            group_id = groups_by_name.get(ngr)

            # tentar por prefixo (ex: '200')
            if not group_id:
                prefix = grp_text.split("-")[0].strip() if "-" in grp_text else grp_text.strip()
                group_id = groups_by_prefix.get(_norm(prefix))

            # tentar correspondência por substring (flexível)
            if not group_id:
                for gname_norm, gid in groups_by_name.items():
                    if ngr in gname_norm or gname_norm in ngr:
                        group_id = gid
                        break

            if not group_id:
                log_result(f"ERRO: Grupo '{grp_text}' não encontrado (usuário {login_raw})")
                continue

            # verificar se usuário já é membro do grupo (tentar endpoint de members)
            already_member = False
            members_before = []
            def _extract_member_id(m):
                # tenta extrair um id consistente de várias estruturas possíveis
                if isinstance(m, dict):
                    for k in ("id", "Id", "ID", "user", "userId", "user_id", "memberId"):
                        v = m.get(k)
                        if v is None:
                            continue
                        if isinstance(v, dict) and v.get("id") is not None:
                            return str(v.get("id"))
                        return str(v)
                    # casos em que o próprio objeto tem campos conhecidos internamente
                    if "user" in m and isinstance(m["user"], dict) and m["user"].get("id"):
                        return str(m["user"]["id"])
                    # fallback: stringify whole dict
                    return str(m)
                return str(m)

            try:
                members_resp = session.get(f"{MSTR_URL}/usergroups/{group_id}/members", timeout=20)
                if members_resp.status_code == 200:
                    members = members_resp.json()
                    members_before = [_extract_member_id(m) for m in members]
                    # comparação robusta: igualando strings (user_id já é str)
                    if str(user_id) in members_before:
                        already_member = True
                # se endpoint não suportado, prosseguir e tentar patch (será tratado)
            except Exception:
                pass

            if already_member:
                msg = f"INFO: {login_raw} já é membro do grupo '{grp_text}' (id={group_id}) — pulando"
                log_result(msg)
                results.append({
                    "login_raw": login_raw,
                    "login_norm": login_norm,
                    "user_id": user_id,
                    "group_requested": grp_text,
                    "group_id": group_id,
                    "members_before": ",".join(members_before),
                    "members_after": ",".join(members_before),
                    "action": "already_member",
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                })
                continue

            # usar payload compatível com o REST API (lista de ids) — segue padrão de outros scripts
            patch_body = {"operationList": [{"op": "add", "path": "/members", "value": [str(user_id)]}]}
            try:
                patch_resp = session.patch(f"{MSTR_URL}/usergroups/{group_id}", json=patch_body, timeout=30)
                if patch_resp.status_code in (200, 204, 201, 202):
                    # tentar buscar membros novamente para registrar estado "after"
                    members_after = None
                    try:
                        members_resp2 = session.get(f"{MSTR_URL}/usergroups/{group_id}/members", timeout=20)
                        if members_resp2.status_code == 200:
                            members2 = members_resp2.json()
                            members_after = [str(m.get('id')) if isinstance(m, dict) and m.get('id') is not None else str(m) for m in members2]
                    except Exception:
                        members_after = None

                    if members_after is None:
                        # inferir
                        members_after = list(dict.fromkeys(members_before + [str(user_id)]))

                    msg = f"SUCESSO: {login_raw} adicionado ao grupo '{grp_text}' (id={group_id})"
                    log_result(msg)
                    results.append({
                        "login_raw": login_raw,
                        "login_norm": login_norm,
                        "user_id": user_id,
                        "group_requested": grp_text,
                        "group_id": group_id,
                        "members_before": ",".join(members_before),
                        "members_after": ",".join(members_after),
                        "action": "added",
                        "message": msg,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    msg = f"ERRO: Falha ao adicionar {login_raw} ao grupo '{grp_text}' (id={group_id}) - status {patch_resp.status_code} - {patch_resp.text}"
                    log_result(msg)
                    results.append({
                        "login_raw": login_raw,
                        "login_norm": login_norm,
                        "user_id": user_id,
                        "group_requested": grp_text,
                        "group_id": group_id,
                        "members_before": ",".join(members_before),
                        "members_after": ",".join(members_before),
                        "action": "error",
                        "message": msg,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                msg = f"ERRO: Exceção ao adicionar {login_raw} ao grupo '{grp_text}' - {e}"
                log_result(msg)
                results.append({
                    "login_raw": login_raw,
                    "login_norm": login_norm,
                    "user_id": user_id,
                    "group_requested": grp_text,
                    "group_id": group_id,
                    "members_before": ",".join(members_before),
                    "members_after": ",".join(members_before),
                    "action": "exception",
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                })

    # 6) Salvar resultado em Excel (antes do logout)
    try:
        if results:
            df_out = pd.DataFrame(results)
            out_name = f"assign_users_groups_before_after_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            out_path = os.path.join(os.path.dirname(__file__), out_name)
            try:
                df_out.to_excel(out_path, index=False)
                log_result(f"INFO: Resultados salvos em {out_path}")
            except Exception as e:
                log_result(f"ERRO: Falha ao salvar Excel de resultados: {e}")
    except Exception:
        pass

    # 7) Logout
    try:
        session.post(f"{MSTR_URL}/auth/logout", timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()
