

import requests
import json

# --- CONFIGURAÇÃO ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
PROJECT_ID = "239BC40211E8B1E3626F0080EF95EED2"
USER = "31071655817"
PASS = "Tera!7777"

def get_session():
    url = f"{BASE_URL}/api/auth/login"
    data = {"username": USER, "password": PASS, "loginMode": 1}
    response = requests.post(url, json=data)
    return response.headers.get("X-MSTR-AuthToken")

def compare_attribute_properties(id1, id2):
    token = get_session()
    headers = {"X-MSTR-AuthToken": token, "X-MSTR-ProjectID": PROJECT_ID}
    
    # Busca os objetos
    resp1 = requests.get(f"{BASE_URL}/api/objects/{id1}?type=12", headers=headers).json()
    resp2 = requests.get(f"{BASE_URL}/api/objects/{id2}?type=12", headers=headers).json()
    
    # NA API MSTR, o conteúdo do atributo geralmente está na raiz do JSON retornado
    # Se o JSON for uma lista ou tiver uma estrutura aninhada, ajustaremos aqui
    obj1 = resp1
    obj2 = resp2
    
    # Compara todas as chaves existentes
    todas_chaves = set(obj1.keys()) | set(obj2.keys())
    
    print(f"{'Propriedade':<25} | {'Status'}")
    print("-" * 60)
    
    for key in todas_chaves:
        # Ignora chaves técnicas de resposta de API (como ticketId, code, etc)
        if key in ['ticketId', 'code', 'message']: continue
        
        v1 = obj1.get(key)
        v2 = obj2.get(key)
        
        if v1 != v2:
            print(f"{key:<25} | DIFERENTE")
            print(f"   -> Atributo Trava: {v1}")
            print(f"   -> Atributo CNPJ:  {v2}")
        else:
            # Opcional: print(f"{key:<25} | Igual")
            pass

# Execução
compare_attribute_properties("22DC161D4B7CC052583C21A68F948A7A", "395A8EC04500A0B3CC79CA8FB50B76DB")