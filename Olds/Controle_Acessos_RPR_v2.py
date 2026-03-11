# Script em Python
# Versão 1.0 (V1.0)

# O tempo total de execução está entre 08 / 10 Minutos

# Para editar/executar o código abaixo, é necessário fazer o download de qualquer IDE. Para esta versão, foi utilizado a IDE chamada VSCode
# Após a instalação da IDE é necessário instalar alguns módulos que foram utilizados no programa.

# Importação de módulos
# Para instalar os módulos abaixo, basta entrar no CMD e digitar o seguinte comando pip install nome_do_modulo


import os
import teradatasql
import pandas as pd
import requests
import json


import logging
from datetime import datetime

data_log = datetime.now().strftime('%Y%m%d_%H%M%S')

logging.basicConfig(
                    level=logging.INFO,
                    format="{asctime} - {levelname} - {message}", 
                    datefmt='%d-%b-%y %H:%M:%S',
                    style="{",
                    filename=f"logs/Logging_teste_{data_log}.log",
                    filemode="w",
                    )


# Variável que define qual o tipo de aplicação que irá ser executada - MicroStrategy REST API
headers = {
    'Accept': 'application/json',
    }

# Variável que guarda os parâmetros de conexão do usuário no REST API
json_data = {
    'username': '31071655817',
    'password': 'Tera!7777',
    'loginMode': 1,
    'applicationType': 35,
    }

# Variável que define quais parâmetros dos grupos estamos listando, para utilização posterior. Todo comando a ser executado na REST API do MicroStrategy, necessita da utilização de ID's.( id, nome, etc )
group_params = {
    'limit': '-1',
    'fields': 'id,name',
    }

# Variável que define quais parâmetros dos usuários estamos listando. ( id, nome, abbreviation[essa variável é responsável por armazenar o login do usuário no MicroStrategy, ou seja, o CPF] )
users_params =  {
     #'limit': '-1',
     'fields': 'name,abbreviation,enabled',
    }

# Abre uma sessão para executar todo o script. Sem essa sessão, fica dando time out entre as páginas do REST API 
client_session = requests.session()

# Variável responsável por fazer a autenticação no REST API. Essa variável gera o TOKEN a ser utilizado ao longo do script
response = client_session.post('http://10.14.203.158:8080/SEFADEVLIB/api/auth/login', headers=headers, json=json_data)

# Variável responsável por guardar o TOKEN gerado anteriormente
new_header = { 'X-MSTR-AuthToken': response.headers['X-MSTR-AuthToken'],
               'Accept': 'application/json', 
               'Content-Type': 'application/json',
    }

# # Variável que pega os nomes e ids dos grupos de usuários
# mstr_group_ids_names = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups', params=group_params, headers=new_header)

# # Variável que lista todos os grupos de usuários e seus IDs
# mstr_group_names = mstr_group_ids_names.json()

# Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON)
todos_usuarios_mstr = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/users', params=users_params, headers=new_header)
usuarios_mstr = todos_usuarios_mstr.json()

logging.info(usuarios_mstr)

#print(usuarios_mstr)



# # Variável responsável por armazenar apenas os IDS dos grupos do MicroStrategy, que estão dentro ta tabela do Teradata. 
# # Essa verificação é feita apenas pelo CD_GRUPO (Banco de dados) e os 3 primeiros números do nome do grupo no MicroStrategy
# lista_id_mstr_groups = []

# for td_info in teradata_codigo_grupo:
#     #print(td[0])
    
#     for mstr_info in mstr_group_names:
#         #print(mstr['name'])
#         if mstr_info['name'].split('-')[0].strip() == td_info[0]:
#            # print(mstr['id'])
#            lista_id_mstr_groups.append(mstr_info['id'])


# # Variável que converte os dados da variável anterior em uma variável do tipo lista.
# # Variável do tipo lista, permite fazer filtros
# mstr_groups_ids = list(lista_id_mstr_groups)

