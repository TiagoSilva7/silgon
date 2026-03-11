import requests
import pandas as pd
import os
import time

# --- CONFIGURAÇÕES ---
base_url = "http://10.14.203.158:8080/SEFAPRODLIB/api"
username_api = "31071655817"
password_api = "Tera!7777"
login_mode = 1
device_id = "1D2E6D168A7711D4BE8100B0D04B6F0B"

def get_auth_token():
    url = f"{base_url}/auth/login"
    payload = {"username": username_api, "password": password_api, "loginMode": login_mode}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 204:
            return response.headers['X-MSTR-AuthToken'], response.cookies
    except Exception as e:
        print(f"Erro na conexão: {e}")
    return None, None

def delete_old_addresses(token, cookies, user_id):
    """Busca e apaga endereços existentes para evitar duplicidade"""
    url = f"{base_url}/users/{user_id}/addresses"
    headers = {"X-MSTR-AuthToken": token}
    try:
        resp = requests.get(url, headers=headers, cookies=cookies)
        if resp.status_code == 200:
            addresses = resp.json().get('addresses', [])
            for addr in addresses:
                addr_id = addr.get('id')
                # Apaga se o nome for o genérico anterior ou se quiser limpar tudo antes de recriar
                del_url = f"{url}/{addr_id}"
                requests.delete(del_url, headers=headers, cookies=cookies)
    except:
        pass

def add_new_address(token, cookies, user_id, email_address, user_name):
    """Cria o endereço com o nome do usuário"""
    url = f"{base_url}/users/{user_id}/addresses"
    headers = {"X-MSTR-AuthToken": token, "Content-Type": "application/json"}
    
    payload = {
        "name": user_name,            # Agora usa o nome do usuário do Excel
        "value": str(email_address).strip(),
        "deliveryMode": "EMAIL",
        "deviceId": device_id,
        "isDefault": True
    }
    
    resp = requests.post(url, headers=headers, cookies=cookies, json=payload)
    return resp.status_code

# --- EXECUÇÃO ---
token, cookies = get_auth_token()

if token:
    print("🔓 Autenticado. Iniciando Limpeza e Atualização...")
    try:
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_excel = os.path.join(diretorio_atual, 'Lista_Oficial_att.xlsx')

        df = pd.read_excel(caminho_excel).dropna(how='all')
        df.columns = [str(c).strip().lower() for c in df.columns]

        col_nome = next((c for c in df.columns if 'nome' in c), None)
        col_email = next((c for c in df.columns if 'email' in c), None)

        if col_nome and col_email:
            for index, row in df.iterrows():
                nome_excel = str(row[col_nome]).strip()
                email_excel = str(row[col_email]).strip()
                
                if nome_excel.lower() == 'nan': continue

                # 1. Busca ID do Usuário
                url_search = f"{base_url}/users"
                params = {"searchPattern": nome_excel}
                user_res = requests.get(url_search, headers={"X-MSTR-AuthToken": token}, cookies=cookies, params=params)
                
                user_id = None
                for u in user_res.json():
                    if u['name'].strip().lower() == nome_excel.lower():
                        user_id = u['id']
                        break
                
                if user_id:
                    # 2. LIMPEZA: Apaga endereços antigos primeiro
                    delete_old_addresses(token, cookies, user_id)
                    
                    # 3. CRIAÇÃO: Adiciona com o nome correto
                    status = add_new_address(token, cookies, user_id, email_excel, nome_excel)
                    
                    if status in [200, 201]:
                        print(f"[{index+1}] {nome_excel}: ✅ Limpo e Atualizado")
                    else:
                        print(f"[{index+1}] {nome_excel}: ❌ Erro ao criar ({status})")
                else:
                    print(f"[{index+1}] {nome_excel}: ❓ Não encontrado")
                
                time.sleep(0.1) # Pausa curta para estabilidade

    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        requests.post(f"{base_url}/auth/logout", headers={"X-MSTR-AuthToken": token}, cookies=cookies)
        print("\nSessão encerrada.")
else:
    print("Falha no login.")