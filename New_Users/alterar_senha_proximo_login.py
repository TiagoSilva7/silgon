import requests
import pandas as pd
import os
import time

# --- CONFIGURAÇÕES ---
base_url = "http://10.14.203.158:8080/SEFAPRODLIB/api"
username_api = "31071655817"
password_api = "Tera!7777"
NOME_ARQUIVO_EXCEL = 'Lista_Oficial_att_new_groups.xlsx'

def get_auth():
    url = f"{base_url}/auth/login"
    payload = {"username": username_api, "password": password_api, "loginMode": 1}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 204:
            return res.headers['X-MSTR-AuthToken'], res.cookies
    except Exception as e:
        print(f"Erro de conexão: {e}")
    return None, None

def set_force_password_change(token, cookies, user_id):
    """Apenas marca a caixa de trocar senha, sem alterar a senha atual"""
    url = f"{base_url}/users/{user_id}"
    headers = {
        "X-MSTR-AuthToken": token,
        "Content-Type": "application/json"
    }
    # Use the REST API's operationList format to update user properties.
    # The field used when creating users is `requireNewPassword`, so we replace that.
    payload = {
        "operationList": [
            {"op": "REPLACE", "path": "/requireNewPassword", "value": True}
        ]
    }
    res = requests.patch(url, headers=headers, cookies=cookies, json=payload)
    # return status and body text for better diagnostics
    return res.status_code, (res.text or '')

# --- EXECUÇÃO ---
token, cookies = get_auth()
resultados_final = []

if token:
    print("🔓 Autenticado. Iniciando busca por Login/Abbreviation...")
    try:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        caminho_completo = os.path.join(dir_path, NOME_ARQUIVO_EXCEL)

        if not os.path.exists(caminho_completo):
            print(f"❌ Arquivo '{NOME_ARQUIVO_EXCEL}' não encontrado.")
        else:
            # Lendo o Excel e garantindo que o login seja tratado sem zeros à esquerda
            df = pd.read_excel(caminho_completo)
            df.columns = [str(c).strip().lower() for c in df.columns]
            col_login = next((c for c in df.columns if 'login' in c), None)

            if col_login:
                # Tratamento: Converte para string, remove decimais se houver, e tira zeros à esquerda
                logins_procurados = df[col_login].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip('0').unique()
                print(f"📋 Total de logins únicos para processar: {len(logins_procurados)}")

                # Para garantir performance e precisão, vamos buscar os usuários do servidor
                # filtrando pelo abbreviation (login)
                for login_limpo in logins_procurados:
                    if login_limpo == 'nan' or not login_limpo: continue

                    # Busca o usuário que tem esse abbreviation exato
                    search_url = f"{base_url}/users"
                    # Usamos searchPattern com o login limpo
                    s_res = requests.get(search_url, headers={"X-MSTR-AuthToken": token}, 
                                         cookies=cookies, params={"searchPattern": login_limpo})
                    
                    user_id = None
                    nome_encontrado = "Desconhecido"
                    
                    # Validação rigorosa: o abbreviation tem que ser igual ao login do excel
                    if s_res.status_code == 200:
                        for u in s_res.json():
                            # Algumas APIs retornam o login no campo 'abbreviation'
                            if str(u.get('abbreviation', '')).lstrip('0') == login_limpo:
                                user_id = u['id']
                                nome_encontrado = u['name']
                                break

                    if user_id:
                        status_code, resp_text = set_force_password_change(token, cookies, user_id)
                        if status_code in (200, 204):
                            print(f"✅ Login {login_limpo} ({nome_encontrado}): Flag de senha ativada.")
                            status_msg = "Sucesso"
                        else:
                            print(f"❌ Login {login_limpo}: Erro na API ({status_code}) - {resp_text}")
                            status_msg = f"Erro {status_code}: {resp_text}"
                    else:
                        print(f"⚠️ Login {login_limpo}: Usuário não encontrado no MicroStrategy.")
                        status_msg = "Não encontrado"

                    resultados_final.append({
                        "Login Original Excel": login_limpo,
                        "Nome no MSTR": nome_encontrado,
                        "Alterar Senha Ativado": "Sim" if status_msg == "Sucesso" else "Não",
                        "Status": status_msg
                    })
                    time.sleep(0.05)

                # Gerar Relatório de Saída
                df_saida = pd.DataFrame(resultados_final)
                df_saida.to_excel(os.path.join(dir_path, 'Resultado_Filtro_Login.xlsx'), index=False)
                print(f"\n🚀 Finalizado! Relatório gerado: Resultado_Filtro_Login.xlsx")

            else:
                print("❌ Coluna 'login' não encontrada no Excel.")

    except Exception as e:
        print(f"💥 Erro: {e}")
    finally:
        requests.post(f"{base_url}/auth/logout", headers={"X-MSTR-AuthToken": token}, cookies=cookies)
else:
    print("Falha no login da API.")