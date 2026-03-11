import os
import requests
import pandas as pd
import unicodedata
from datetime import datetime
import logging

# Config
MSTR_URL = os.environ.get("MSTR_URL", "http://10.14.203.158:8080/SEFAPRODLIB/api")
ADMIN_USER = os.environ.get("MSTR_ADMIN_USER", "31071655817")
ADMIN_PASS = os.environ.get("MSTR_ADMIN_PASS", "SENHA")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "Lista_Oficial_att_email.xlsx")
LOG_PATH = os.path.join(os.path.dirname(__file__), "log_add_delivery_emails.log")

logging.basicConfig(level=logging.INFO, filename=LOG_PATH, format="%(asctime)s - %(levelname)s - %(message)s")


def log_result(msg):
    logging.info(msg)
    print(msg)


def _normalize_col(name: str) -> str:
    name = str(name).strip().lower().replace(" ", "_")
    return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')


def _get_field(row, candidates):
    for c in candidates:
        if c in row and pd.notna(row.get(c)):
            return str(row.get(c)).strip()
    return None


def main():
    session = requests.Session()

    # Auth
    try:
        auth_resp = session.post(f"{MSTR_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=30)
        auth_resp.raise_for_status()
    except Exception as e:
        log_result(f"ERRO: Falha na autenticação: {e}")
        return

    auth_token = auth_resp.headers.get("X-MSTR-AuthToken")
    if not auth_token:
        log_result("ERRO: Token de autenticação não retornado.")
        return

    headers = {"X-MSTR-AuthToken": auth_token, "Accept": "application/json", "Content-Type": "application/json"}

    # carregar usuários do MSTR (id,abbreviation)
    try:
        users_resp = session.get(f"{MSTR_URL}/users", params={"limit": "-1", "fields": "id,abbreviation"}, headers=headers, timeout=30)
        users_resp.raise_for_status()
        users = users_resp.json()
    except Exception as e:
        log_result(f"ERRO: Não foi possível obter lista de usuários: {e}")
        return

    users_map = {u.get("abbreviation"): u.get("id") for u in users}
    log_result(f"INFO: {len(users_map)} usuários carregados do MicroStrategy")

    # ler excel
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception as e:
        log_result(f"ERRO: Falha ao ler {EXCEL_PATH}: {e}")
        return

    df.rename(columns=lambda c: _normalize_col(c), inplace=True)
    log_result(f"INFO: Colunas do Excel: {list(df.columns)}")

    for idx, row in df.iterrows():
        login = _get_field(row, ["login", "username", "abbreviation"])
        email = _get_field(row, ["email", "emailaddress", "email_address", "e_mail"]) or _get_field(row, ["mail"])

        if not login:
            log_result(f"AVISO: Linha {idx+2} sem coluna de login — pulando")
            continue
        if not email:
            log_result(f"AVISO: Linha {idx+2} sem email para {login} — pulando")
            continue

        user_id = users_map.get(login)
        if not user_id:
            log_result(f"ERRO: Usuário '{login}' não encontrado no MicroStrategy — verifique abreviação")
            continue

        # garantia: email format
        if "@" not in email:
            email = f"{email}@dominio.com"

        # 1) tentar atualizar emailAddress (primary)
        try:
            patch_resp = session.patch(f"{MSTR_URL}/users/{user_id}", headers=headers, json={"emailAddress": email}, timeout=30)
            if patch_resp.status_code in (200, 204):
                log_result(f"SUCESSO: primary email atualizado para {login} -> {email}")
            else:
                log_result(f"INFO: PATCH primary email retornou {patch_resp.status_code} para {login}: {patch_resp.text}")

                # Se a API requer um operationList, primeiramente buscar o recurso para descobrir o campo correto
                try:
                    # O endpoint não aceita 'fields=*' — remover param para obter o recurso
                    get_user_resp = session.get(f"{MSTR_URL}/users/{user_id}", headers=headers, timeout=30)
                    if get_user_resp.status_code == 200:
                        try:
                            user_obj = get_user_resp.json()
                            log_result(f"DEBUG: Estrutura do usuário (parcial) para {login}: {list(user_obj.keys())}")

                            # tentar encontrar uma chave que contenha 'email'
                            candidate_keys = [k for k in user_obj.keys() if 'email' in k.lower()]
                            tried = False
                            for k in candidate_keys:
                                path = f"/{k}"
                                op_payload = {"operationList": [{"op": "replace", "path": path, "value": email}]}
                                try:
                                    op_resp = session.patch(f"{MSTR_URL}/users/{user_id}", headers=headers, json=op_payload, timeout=30)
                                    tried = True
                                    if op_resp.status_code in (200, 204):
                                        log_result(f"SUCESSO: primary email atualizado via operationList path={path} para {login} -> {email}")
                                        break
                                    else:
                                        log_result(f"DEBUG: operationList PATCH path={path} retornou {op_resp.status_code} - {op_resp.text}")
                                except Exception as e2:
                                    log_result(f"DEBUG: exception ao tentar operationList PATCH path={path} - {e2}")

                            if not tried:
                                # tentar caso onde email esteja dentro de 'properties' ou similar
                                if 'properties' in user_obj and isinstance(user_obj['properties'], dict):
                                    for k in user_obj['properties'].keys():
                                        if 'email' in k.lower():
                                            path = f"/properties/{k}"
                                            op_payload = {"operationList": [{"op": "replace", "path": path, "value": email}]}
                                            op_resp = session.patch(f"{MSTR_URL}/users/{user_id}", headers=headers, json=op_payload, timeout=30)
                                            if op_resp.status_code in (200, 204):
                                                log_result(f"SUCESSO: primary email atualizado via operationList path={path} para {login} -> {email}")
                                                tried = True
                                                break
                                            else:
                                                log_result(f"DEBUG: operationList PATCH path={path} retornou {op_resp.status_code} - {op_resp.text}")

                            if not tried:
                                log_result(f"AVISO: Não encontrei campo 'email' diretamente editável no recurso do usuário {login}. Resposta GET foi: {get_user_resp.text}")
                        except Exception:
                            log_result(f"DEBUG: GET /users/{user_id} retornou não-json: {get_user_resp.text}")
                    else:
                        log_result(f"DEBUG: GET /users/{user_id} retornou {get_user_resp.status_code} - {get_user_resp.text}")
                except Exception as e2:
                    log_result(f"ERRO: Exceção ao tentar descobrir campo para operationList PATCH para {login}: {e2}")
        except Exception as e:
            log_result(f"ERRO: Exceção ao atualizar primary email para {login}: {e}")

        # 2) tentar adicionar como endereço de delivery (vários formatos de payload)
        added = False
        # Tentar payloads que reflitam os campos vistos na UI: Name, Physical Address, Delivery Type, Device
        # Primary attempt: set 'name' to the user's login and physicalAddress to the email
        payloads = [
            ( {"name": login, "physicalAddress": email, "deliveryType": "EMAIL", "device": "GENERIC_EMAIL", "setAsDefault": False}, f"{MSTR_URL}/users/{user_id}/addresses" ),
            # alternative fields some APIs accept
            ( {"name": login, "address": email, "type": "email", "login": login}, f"{MSTR_URL}/users/{user_id}/addresses" ),
            ( {"name": login, "physicalAddress": email, "deliveryType": "EMAIL", "device": "GENERIC_EMAIL", "abbreviation": login}, f"{MSTR_URL}/users/{user_id}/addresses" ),
            ( {"emailAddress": email, "name": login}, f"{MSTR_URL}/users/{user_id}/deliveryaddresses" ),
            ( {"address": email}, f"{MSTR_URL}/users/{user_id}/addresses" )
        ]

        last_payload = None
        for payload, url in payloads:
            try:
                post_resp = session.post(url, headers=headers, json=payload, timeout=30)
                if post_resp.status_code in (200, 201, 204):
                    log_result(f"SUCESSO: endereço de delivery adicionado para {login} via {url}")
                    added = True
                    last_payload = payload
                    break
                else:
                    log_result(f"DEBUG: tentativa {url} retornou {post_resp.status_code} - {post_resp.text}")
            except Exception as e:
                log_result(f"DEBUG: tentativa {url} gerou exceção: {e}")

        if not added:
            log_result(f"AVISO: Não foi possível adicionar {email} como endereço de delivery para {login} — verificar API do MicroStrategy")
        else:
            # Verificar via GET se o endereço realmente aparece
            try:
                get_resp = session.get(f"{MSTR_URL}/users/{user_id}/addresses", headers=headers, timeout=20)
                if get_resp.status_code == 200:
                    try:
                        addresses = get_resp.json()
                        # procurar por physicalAddress ou address contendo o email
                        found = False
                        for a in addresses:
                            # campos possíveis: 'physicalAddress', 'address', 'emailAddress'
                            vals = []
                            if isinstance(a, dict):
                                vals.extend([str(a.get(k,"")).lower() for k in ("physicalAddress","address","emailAddress","name")])
                            else:
                                vals.append(str(a).lower())
                            if any(email.lower() in v for v in vals if v):
                                found = True
                                break
                        if found:
                            log_result(f"VERIFICACAO: endereço aparece em GET /users/{user_id}/addresses para {login}")
                        else:
                            log_result(f"VERIFICACAO: endereço NÃO encontrado em GET /users/{user_id}/addresses para {login} (resposta listada)")
                            log_result(f"DEBUG: resposta GET: {addresses}")
                            # Tentar fallback: usar PATCH operationList add em /addresses com o payload usado no POST
                            if last_payload is not None:
                                try:
                                    op_payload = {"operationList": [{"op": "add", "path": "/addresses", "value": [last_payload]}]}
                                    op_resp = session.patch(f"{MSTR_URL}/users/{user_id}", headers=headers, json=op_payload, timeout=30)
                                    if op_resp.status_code in (200, 204):
                                        log_result(f"FALLBACK SUCESSO: adicionado via operationList /addresses para {login}")
                                    else:
                                        log_result(f"FALLBACK ERRO: operationList PATCH retornou {op_resp.status_code} - {op_resp.text}")
                                except Exception as e:
                                    log_result(f"FALLBACK ERRO: exceção ao tentar operationList PATCH /addresses para {login}: {e}")
                    except Exception:
                        log_result(f"DEBUG: GET /users/{user_id}/addresses retornou não-json: {get_resp.text}")
                else:
                    log_result(f"DEBUG: GET /users/{user_id}/addresses retornou {get_resp.status_code} - {get_resp.text}")
            except Exception as e:
                log_result(f"DEBUG: Falha ao verificar addresses via GET para {login}: {e}")

    # logout
    try:
        session.post(f"{MSTR_URL}/auth/logout", headers=headers, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()
