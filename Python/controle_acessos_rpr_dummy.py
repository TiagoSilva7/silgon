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
from datetime import datetime, timedelta
import sys
import teradata

def print_logging(tipo, *args):
    data_log = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(data_log + ": " + tipo, *args)

def print_info(*args):
    print_logging("INFO", *args)

def print_erro(*args):
    print_logging("ERROR", *args)

def sair():
    os.sys.exit(0)

def finalizar(codigo):
    os.sys.exit(codigo)

def load_parametros():
        os.chdir(os.path.dirname(__file__))
        dir_atual = os.getcwd()
        arq_param=dir_atual+'/rpr_params.json'
    
        with open(arq_param) as f:
            var = json.load(f)
            return var

def main():

    global json_var
    json_var=load_parametros()

    dt_inicio = datetime.now()

    # Variável que define qual o tipo de aplicação que irá ser executada - MicroStrategy REST API
    headers = {
        'Accept': 'application/json',
        }

    # Variável que guarda os parâmetros de conexão do usuário no REST API
    json_data = {
        'username': 'integracao_receitapr',
        'password': 'sefacreint123',
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
        'limit': '-1',
        'fields': 'id,name,abbreviation',
        }
    # Variável que define quais grupos cada usuário pertence para utilização posterior. Todo comando a ser executado na REST API do MicroStrategy, necessita da utilização de ID's.( id, memberships, etc )
    users_params_groups = {
        'fields': 'id,memberships',
        }
    # Abre uma sessão para executar todo o script. Sem essa sessão, fica dando time out entre as páginas do REST API 
    client_session = requests.session()

    ## Variável responsável por fazer a autenticação no REST API. Essa variável gera o TOKEN a ser utilizado ao longo do script - Desenvolvimento
    #response = client_session.post('http://10.14.203.158:8080/SEFADEVLIB/api/auth/login', headers=headers, json=json_data)
    
    # Variável responsável por fazer a autenticação no REST API. Essa variável gera o TOKEN a ser utilizado ao longo do script - Produção
    response = client_session.post('http://10.14.203.158:8080/SEFAPRODLIB_TESTE/api/auth/login', headers=headers, json=json_data)

    # Variável responsável por guardar o TOKEN gerado anteriormente
    new_header = { 'X-MSTR-AuthToken': response.headers['X-MSTR-AuthToken'],
                'Accept': 'application/json', 
                'Content-Type': 'application/json',
        }

    ## Variável que pega os nomes e ids dos grupos de usuários - Desenvolvimento
    mstr_group_ids_names = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups', params=group_params, headers=new_header)

    # Variável que pega os nomes e ids dos grupos de usuários - Produção
    #mstr_group_ids_names = client_session.get('http://10.14.203.158:8080/SEFAPRODLIB_TESTE/api/usergroups', params=group_params, headers=new_header)

    # Variável que lista todos os grupos de usuários e seus IDs
    mstr_group_names = mstr_group_ids_names.json()

    ## Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON) - Desenvolvimento
    #todos_usuarios_mstr = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/users', params=users_params, headers=new_header)
   
    # Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON) - Produção
    todos_usuarios_mstr = client_session.get('http://10.14.203.158:8080/SEFAPRODLIB_TESTE/api/users', params=users_params, headers=new_header)
    usuarios_mstr = todos_usuarios_mstr.json()

    #Variável que armazena todos os usuários distintos do MicroStrategy, para remoção dos usuários sem grupos, no fim do código
    lista_id_usuarios_mstr = []

    for usuario_distinto_microstrategy in usuarios_mstr:
        lista_id_usuarios_mstr.append(usuario_distinto_microstrategy['id'])
    
    
    print_info("#####################################")
    print_info("CPF todos Usuários MicroStrategy")
    print_info("#####################################")

    for cpf_usuario_microstrategy in sorted([obj_json['abbreviation'] for obj_json in usuarios_mstr]):
        print_info(cpf_usuario_microstrategy)

    dt_fim = datetime.now()
    dt_total = str(dt_fim - dt_inicio)

    print_info("#####################################")
    print_info("Script executado com sucesso!!!")
    print_info("Tempo de execução: " + dt_total)
    print_info("#####################################")

    ########################################################################################################################################################################

if __name__ == '__main__':
    main()











