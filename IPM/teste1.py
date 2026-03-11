import requests
import json
import urllib3
import re
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES DE AMBIENTE ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
PROJECT_ID = "239BC40211E8B1E3626F0080EF95EED2"
USERNAME = "USER"
PASSWORD = "PASSWORD" 
DB_ROLE_ID = "00ADF1DB4154E738C68A1A85EF051258"
FOLDER_ID = "85AC4A2D49E1B8CBE678C4B14C51DB72" 

INPUT_DIR = r"C:\Users\tg186031\Downloads\IPM"

def extrair_colunas_sql(sql):
    match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
    if not match: return []
    cols_part = match.group(1)
    raw_cols = [c.strip() for c in cols_part.split(",") if c.strip()]
    return [c.split()[-1].strip().strip("\"`").split('.')[-1].upper() for c in raw_cols]

# 1. LOGIN
session = requests.Session()
r_login = session.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD, "loginMode": 1}, verify=False)
if r_login.status_code != 204:
    print("❌ Falha crítica no login.")
    exit()

token = r_login.headers.get('X-MSTR-AuthToken')
headers = {"X-MSTR-AuthToken": token, "X-MSTR-ProjectID": PROJECT_ID, "Content-Type": "application/json"}
print("🔑 Sessão iniciada.")

try:
    arquivos_sql = [f for f in os.listdir(INPUT_DIR) if f.endswith(".sql")]
    print(f"📂 Processando {len(arquivos_sql)} arquivos...\n")

    for arquivo in arquivos_sql:
        caminho_full = os.path.join(INPUT_DIR, arquivo)
        nome_relatorio = os.path.splitext(arquivo)[0].upper()
        
        with open(caminho_full, 'r', encoding='utf-8') as f:
            sql_query = f.read().strip().rstrip(";")

        col_names = extrair_colunas_sql(sql_query)
        columns, attributes, metrics = [], [], []

        for col in col_names:
            precision, scale = None, None
            
            # --- LÓGICA DE TIPAGEM CORRIGIDA ---
            if "CNPJ" in col or "CPF" in col:
                dtype, dformat = "double", "number"
            elif col.startswith("VL_"):
                dtype, precision, scale, dformat = "numeric", 18, 2, "number"
            elif col.startswith("DS_"):
                dtype = "variable_length_string"
                precision = 255
                dformat = "text"
            elif col == "ANO" or col.startswith(("ANO_", "CD_")):
                dtype, dformat = "integer", "number"
            elif col.startswith("NU_"):
                dtype, dformat = "double", "number"
            elif col.startswith("DT_"):
                dtype, dformat = "date", "date"
            else:
                dtype = "variable_length_string"
                precision = 255
                dformat = "text"

            col_def = {"name": col, "dataType": {"type": dtype}}
            if precision: col_def["dataType"]["precision"] = precision
            if scale: col_def["dataType"]["scale"] = scale
            
            columns.append(col_def)
            
            is_metric = col.startswith(("VL_", "QT_"))
            obj_name = f"{nome_relatorio}__{col}"

            if is_metric:
                metrics.append({
                    "name": obj_name,
                    "dataType": col_def["dataType"],
                    "expression": {"tree": {"type": "column_reference", "name": col}}
                })
            else:
                attributes.append({
                    "name": obj_name,
                    "forms": [{
                        "id": "45C11FA478E745FEA08D781CEA190FE5", "category": "ID", "type": "system",
                        "displayFormat": dformat, "expression": {"tree": {"type": "column_reference", "name": col}}
                    }]
                })

        # CRIAÇÃO E MATERIALIZAÇÃO
        report_def = {
            "information": {"name": nome_relatorio},
            "sourceType": "custom_sql_free_form",
            "dataSource": {
                "table": {
                    "physicalTable": {
                        "sqlExpression": {
                            "tree": {"type": "operator", "function": "concat_no_blank", 
                                     "children": [{"type": "constant", "variant": {"type": "string", "value": sql_query}}]}
                        },
                        "columns": columns,
                    },
                    "attributes": attributes, "metrics": metrics,
                    "dataSource": {"objectId": DB_ROLE_ID, "subType": "db_role"}
                }
            }
        }

        print(f"⏳ Criando: {nome_relatorio}...")
        r_create = session.post(f"{BASE_URL}/model/reports", headers=headers, json=report_def, verify=False)
        
        if r_create.status_code == 201:
            report_id = r_create.json()['information']['objectId']
            instance_id = r_create.headers.get('X-MSTR-MS-Instance')
            
            save_headers = headers.copy()
            save_headers["X-MSTR-MS-Instance"] = instance_id
            r_save = session.post(f"{BASE_URL}/model/reports/{report_id}/instances/saveAs", 
                                  headers=save_headers, 
                                  json={"name": nome_relatorio, "destinationFolderId": FOLDER_ID}, 
                                  verify=False)
            
            if r_save.status_code == 201:
                print(f"✅ Criado: {nome_relatorio}")
            else:
                print(f"❌ Erro SaveAs [{nome_relatorio}]: {r_save.text}")
        else:
            print(f"❌ Erro Definição [{nome_relatorio}]: {r_create.text}")

finally:
    # DERRUBA SESSÃO SEMPRE
    session.post(f"{BASE_URL}/auth/logout", headers=headers, verify=False)
    print("\n🔒 Sessão encerrada.")