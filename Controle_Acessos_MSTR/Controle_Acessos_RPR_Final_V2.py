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
import sys
import teradata

data_log = datetime.now().strftime('%Y%m%d_%H%M%S')

stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [stdout_handler]

logging.basicConfig(
                    level=logging.INFO,
                    format="{asctime} - {levelname} - {message}", 
                    datefmt='%d-%b-%y %H:%M:%S',
                    style="{",
                    #filename=f"logs/Logging_message_{data_log}.log",
                    handlers=handlers,
                    )

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

    logging.info("#####################################")
    logging.info("Status conexão com a tabela de grupo e usuários")
    logging.info("#####################################")

    # Conexão com o Teradata para buscar as informações dentro das tabelas dos grupos de usuários
    # try:
    #     with teradatasql.connect(host=json_var['TD_HOST'], user=json_var['TD_USER'], password=json_var['TD_PWD']) as connect:
    #         teradata_table = pd.read_sql("SELECT DISTINCT A.CD_GRUPO_RPR, A.NU_CPF_USUAR_RPR \n FROM \n (SELECT \n LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0') AS NU_CPF_USUAR_RPR,\n LPAD(CAST(SUR.CD_GRUPO_RPR as VARCHAR(3)), 3, '0') as CD_GRUPO_RPR,\n GUR.NM_GRUPO_RPR,\n SUR.DS_STATUS_USUAR_RPR, \n CASE WHEN RHF.CD_SIT_FUNC = 1 THEN 'true' ELSE 'false' END AS DS_STATUS_RH \n FROM \n D_TGTDB.ERL_STATUS_USUAR_RPR SUR \n JOIN P_ACCDB.DIM_RH_FUNC RHF \n ON (SUR.NU_CPF_USUAR_RPR = RHF.NU_CPF) \n JOIN \n P_ACCDB.DIM_RH_SIT_FUNC RHSF \n ON (RHF.CD_SIT_FUNC = RHSF.CD_SIT_FUNC) \n JOIN D_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR \n ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR) \n ) A", connect)
    #         logging.info("Conexão realizada com sucesso na tabela grupos e usuários")
    # except Exception as log_error_usuario:
    #     logging.error("Erro de acesso a tabela de grupos e usuários: " + str(log_error_usuario))
    #     finalizar(1)

    udaExec = teradata.UdaExec(appName="RPR", version="1.0", logConsole=False, logLevel="ERROR")
    with udaExec.connect(
        method="odbc", \
        system=json_var["TD_HOST"], \
        username=json_var["TD_USER"], \
        password=json_var["TD_PWD"], \
        driver="Teradata Database ODBC Driver 17.10", \
        SSLMode="Disable") as session:
        
        # Conexão com o Teradata para buscar as informações dentro das tabelas dos grupos de usuários
        teradata_table = pd.read_sql("SELECT DISTINCT A.CD_GRUPO_RPR, A.NU_CPF_USUAR_RPR \n FROM \n (SELECT \n LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0') AS NU_CPF_USUAR_RPR,\n LPAD(CAST(SUR.CD_GRUPO_RPR as VARCHAR(3)), 3, '0') as CD_GRUPO_RPR,\n GUR.NM_GRUPO_RPR,\n SUR.DS_STATUS_USUAR_RPR, \n CASE WHEN RHF.CD_SIT_FUNC = 1 THEN 'true' ELSE 'false' END AS DS_STATUS_RH \n FROM \n D_TGTDB.ERL_STATUS_USUAR_RPR SUR \n JOIN D_DIMDB.DM_RH_FUNC RHF \n ON (SUR.NU_CPF_USUAR_RPR = RHF.NU_CPF) \n JOIN \n D_TGTDB.ERL_TR_SIT_FUNC RHSF \n ON (RHF.CD_SIT_FUNC = RHSF.CD_SIT_FUNC) \n JOIN D_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR \n ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR) \n ) A", session)
        
        # Conexão com o Teradata para buscar os status de cada usuário a serem modificados no MicroStrategy
        teradata_stts_users = pd.read_sql("SELECT DISTINCT A.NU_CPF_USUAR_RPR, A.DS_STATUS_RH \n FROM \n (SELECT \n COALESCE(LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0'), LPAD(CAST(RHF.NU_CPF as VARCHAR(11)), 11, '0')) AS NU_CPF_USUAR_RPR,\n LPAD(CAST(SUR.CD_GRUPO_RPR as VARCHAR(3)), 3, '0') as CD_GRUPO_RPR,\n GUR.NM_GRUPO_RPR,\n SUR.DS_STATUS_USUAR_RPR, \n CASE WHEN RHF.CD_SIT_FUNC = 1 THEN 'true' ELSE 'false' END AS DS_STATUS_RH \n FROM \n D_TGTDB.ERL_STATUS_USUAR_RPR SUR \n RIGHT JOIN D_DIMDB.DIM_RH_FUNC RHF \n ON (SUR.NU_CPF_USUAR_RPR = RHF.NU_CPF) \n JOIN \n D_TGTDB.ERL_TR_SIT_FUNC RHSF \n ON (RHF.CD_SIT_FUNC = RHSF.CD_SIT_FUNC) \n LEFT JOIN D_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR \n ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR) \n WHERE RHF.CD_QUADRO = 1 \n) A", session)
                
    # Variável que armazena os códigos dos grupos e usuários de cada grupo recebidos pelo Receita PR. 
    teradata_cd_group = (teradata_table)
    #print(type(teradata_cd_group))

    # Variável que converte a variável acima, cujo o type era DataFrame, em um objeto do tipo lista.
    teradata_codigo_grupo = teradata_cd_group.values.tolist()

    teradata_codigo_grupo_unico = teradata_cd_group['CD_GRUPO_RPR']

    cd_grupos_teradata = []
    for elements in teradata_codigo_grupo_unico:
        if elements not in cd_grupos_teradata:
            cd_grupos_teradata.append(elements)

    cd_grupos_teradata.sort()

    logging.info("#####################################")
    logging.info("Códigos dos grupos da tabela do banco de dados")
    logging.info("#####################################")

    logging.info(cd_grupos_teradata)

    teradata_cpf_unico_teradata = teradata_cd_group['NU_CPF_USUAR_RPR']

    cpf_usuario_teradata = []
    for elements in teradata_cpf_unico_teradata:
        if elements not in cpf_usuario_teradata:
            cpf_usuario_teradata.append(elements)

    cpf_usuario_teradata.sort()


    logging.info("#####################################")
    logging.info("Números de CPF dos usuários da tabela do banco de dados")
    logging.info("#####################################")

    logging.info(cpf_usuario_teradata)


    logging.info("#####################################")
    logging.info("Status conexão com a tabela de status dos usuários")
    logging.info("#####################################")

    # # Conexão com o Teradata para buscar os status de cada usuário a serem modificados no MicroStrategy
    # try:
    #     with teradatasql.connect(host=json_var['TD_HOST'], user=json_var['TD_USER'], password=json_var['TD_PWD']) as connect:
    #         teradata_stts_users = pd.read_sql("SELECT DISTINCT A.NU_CPF_USUAR_RPR, A.DS_STATUS_RH \n FROM \n (SELECT \n COALESCE(LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0'), LPAD(CAST(RHF.NU_CPF as VARCHAR(11)), 11, '0')) AS NU_CPF_USUAR_RPR,\n LPAD(CAST(SUR.CD_GRUPO_RPR as VARCHAR(3)), 3, '0') as CD_GRUPO_RPR,\n GUR.NM_GRUPO_RPR,\n SUR.DS_STATUS_USUAR_RPR, \n CASE WHEN RHF.CD_SIT_FUNC = 1 THEN 'true' ELSE 'false' END AS DS_STATUS_RH \n FROM \n D_TGTDB.ERL_STATUS_USUAR_RPR SUR \n RIGHT JOIN P_ACCDB.DIM_RH_FUNC RHF \n ON (SUR.NU_CPF_USUAR_RPR = RHF.NU_CPF) \n JOIN \n P_ACCDB.DIM_RH_SIT_FUNC RHSF \n ON (RHF.CD_SIT_FUNC = RHSF.CD_SIT_FUNC) \n LEFT JOIN D_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR \n ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR) \n WHERE RHF.CD_QUADRO = 1 \n) A", connect)
    #         logging.info("Conexão realizada com sucesso na tabela de status dos usuários")
    # except Exception as log_error_status:
    #     logging.error("Erro de acesso a tabela de status do usuário: " + str(log_error_status))
    #     finalizar(1)

    # Variável que converte a variável dos status dos usuários, cujo o type era DataFrame, em um objeto do tipo lista.
    teradata_status_usuarios = teradata_stts_users.values.tolist()

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
        'limit': '-1',
        'fields': 'id,name,abbreviation',
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

    # Variável que pega os nomes e ids dos grupos de usuários
    mstr_group_ids_names = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups', params=group_params, headers=new_header)

    # Variável que lista todos os grupos de usuários e seus IDs
    mstr_group_names = mstr_group_ids_names.json()

    # Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON)
    todos_usuarios_mstr = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/users', params=users_params, headers=new_header)
    usuarios_mstr = todos_usuarios_mstr.json()

    logging.info("#####################################")
    logging.info("CPF todos Usuários MicroStrategy")
    logging.info("#####################################")

    for cpf_usuario_microstrategy in sorted([obj_json['abbreviation'] for obj_json in usuarios_mstr]):
        logging.info(cpf_usuario_microstrategy)

    # Variável responsável por armazenar apenas os IDS dos grupos do MicroStrategy, que estão dentro ta tabela do Teradata. 
    # Essa verificação é feita apenas pelo CD_GRUPO (Banco de dados) e os 3 primeiros números do nome do grupo no MicroStrategy
    lista_id_mstr_groups = []

    for td_info in teradata_codigo_grupo:
        #print(td[0])
        
        for mstr_info in mstr_group_names:
            #print(mstr['name'])
            if mstr_info['name'].split('-')[0].strip() == td_info[0]:
            # print(mstr['id'])
               lista_id_mstr_groups.append(mstr_info['id'])

    logging.info("#####################################")
    logging.info("IDs de todos os grupos do Microstrategy que tem o mesmo código de grupo do Banco de Dados")
    logging.info("#####################################")

    # Variável que converte os dados da variável anterior em uma variável do tipo lista.
    # Variável do tipo lista, permite fazer filtros
    mstr_groups_ids = list(lista_id_mstr_groups)

    # Variável que gera uma lista de ids dos grupos únicos para serem salvos no LOG
    ids_unicos_grupos = []
    for elements in mstr_groups_ids:
        if elements not in ids_unicos_grupos:
            ids_unicos_grupos.append(elements)

    # Ordena os usuários para o LOG
    ids_unicos_grupos.sort()

    logging.info(ids_unicos_grupos)


    ######################################################################################################################################################################

    # REMOVE USUÁRIOS DOS GRUPOS

    # Todo comando abaixo, é para deletar todos os usuários de todos os grupos.
    # Média de 6 minutos para executar


    logging.info("#####################################")
    logging.info("Nome dos grupos do MicroStrategy e membros(usuários) retirados")
    logging.info("#####################################")

    # Variável que faz um looping em todos os ids dos grupos, pegando os usuários que pertecem a cada grupo.
    # Cria uma lista com todos os ids de usuários pertencentes a cada grupo, e passando esses ids, como parâmetros para o comando de removendo todos esses usuários de todos os grupos.
    for id_grupos_deleta_usuarios_mstr in mstr_groups_ids:
        #print(id_grupos_deleta_usuarios_mstr)

        users_ids_response = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+id_grupos_deleta_usuarios_mstr+'/members', params=users_params, headers=new_header)
        users_id = users_ids_response.json()

        # Criação de um array de todos os ids dos usuários pertencentes a cada grupo.
        users_complete = []
        #print(users_id)

        # Loop que adiciona os IDs de cada usuário do MicroStrategy dentro do array criado acima
        for usmstr in users_id:
            users_complete.append(usmstr['id'])
        
        # Verifica se não existe usuários na lista criada (USMSTR), ou seja, se a lista está vazia.
        if not users_complete: 
            continue
        
        # Formato do comando de remoção dos usuários do MicroStrategy, de acordo com o REST API
        json_data_remove = {
            "operationList": [
                {
                    "op": "remove",
                    "path": "/members",
                    "value": users_complete,
                },
            ],
        }
        
        # Variável que armazena todas as informações do resultado da execução do REST API de retirada de cada usuário de cada grupo do MicroStrategy.
        remove_usuarios_mstr = client_session.patch('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+id_grupos_deleta_usuarios_mstr, headers=new_header, json=json_data_remove)    
        status_remove_usuarios = remove_usuarios_mstr.json()
        
        # Variáveis apenas das informações para serem adicionadas no LOG
        nm_grupo_removido = "Grupo: " + status_remove_usuarios['abbreviation']
        id_membros_removido = "Membros Removidos: " + str(users_complete)

        logging.info((nm_grupo_removido,id_membros_removido))
    

    ######################################################################################################################################################################

    # ADICIONAR USUÁRIOS

    # Todo comando abaixo é para buscar os usuários dentro do banco de dados, posteriormente buscar os ids deles dentro do MicroStrategy 
    # Por fim, adicionar cada um deles, nos grupos oriundos do banco de dados
    # Média de 4 minutos para executar

    logging.info("#####################################")
    logging.info("Adiciona somente os usuários que estão na tabela do banco de dados")
    logging.info("#####################################")

    # Variável que armazena a combinação dos IDS dos grupos de usuários e usuários do Microstategy, cujo eles são iguais aos que vem da base de usuários do Receita PR
    Lista_ids_grupos_users_td_mstr = []

    for td_groups_users in teradata_codigo_grupo:
        #print(td_groups_users)
        id_group = ''
        id_user = ''
        for mstr_all_groups in mstr_group_names:
            # Verifica se o código do grupo que está no banco de dados é igual ao código do grupo do MicroStrategy
            if mstr_all_groups['name'].split('-')[0].strip() == td_groups_users[0]:
            # Se o código for identico, então, ele guarda o ID do grupo dentro da variável
                id_group = mstr_all_groups['id']
            
        for mstr_users_list_all in usuarios_mstr:
            #print(mstr_users_list_all)
            # Verifica se o CPF do usuário que está no banco de dados é igual ao CPF do usuário do MicroStrategy
            if td_groups_users[1] == mstr_users_list_all['abbreviation']:
                #print(mstr_users_list_all['id'])
                # Se o CPF for identico, então, ele guarda o ID do usuário dentro da variável
                id_user = mstr_users_list_all['id']
        
        # Adiciona a combinação de ID do grupo + Id de usuários daquele grupo, dentro da variável
        Lista_ids_grupos_users_td_mstr.append((id_group, id_user))        

    # Variável que armazena somente os IDs dos usuários do Microstrategy, cujo esses usuários estão na variável Lista_ids_grupos_users_td_mstr (que tem origem do banco de dados).
    usuarios_para_adicionar_no_mstr = {}

    # Tira a duplicidade de usuários para cada grupo do MicroStrategy
    for linhas_distintas in Lista_ids_grupos_users_td_mstr:
        #print(linhas_distintas)
        id_group_lista, id_user_lista = linhas_distintas
        # Verifica se não existe um ID de grupo para determinado usuário, caso não exista, ele adiciona na variável o ID do usuário em forma de LISTA
        if id_group_lista not in usuarios_para_adicionar_no_mstr:
            usuarios_para_adicionar_no_mstr[id_group_lista] = set()
        if id_user_lista:
            usuarios_para_adicionar_no_mstr[id_group_lista].add(id_user_lista)
                
    # Cria um loop para cada item(ID GRUPO e ID USUARIO) da lista criada anteriormente e executa o comando do REST API do MicroStrategy para ir adicionando os usuários aos seus respectivos grupos 
    for grupo_a_ser_adicionado, usuario_a_Ser_Adicionado in usuarios_para_adicionar_no_mstr.items():
    
        # Formato do comando de adição dos usuários do MicroStrategy, de acordo com o REST API
        json_data_add = {
            "operationList": [
                {
                    "op": "add",
                    "path": "/members",
                    "value": list(usuario_a_Ser_Adicionado),
                },
            ],
        }
        
        # Variável que armazena todas as informações do resultado da execução do REST API de adição de usuários dentro de cada grupo do MicroStrategy.
        status_adicao = client_session.patch('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+grupo_a_ser_adicionado, headers=new_header, json=json_data_add)     
        status_adicao_json = status_adicao.json()

        # Verifica se existe erros na inserção de usuários dentro dos grupos
        if 'code' in status_adicao_json:
            id_membros_error = "Membros com erro: " + str(list(usuario_a_Ser_Adicionado))
            logging.error((status_adicao_json, id_membros_error))
        else:
            nm_grupo_add = "Grupo: " + str(status_adicao_json['abbreviation'])
            id_membros_add = "Membros adicionados: " + str(list(usuario_a_Ser_Adicionado))
            logging.info((nm_grupo_add, id_membros_add)) 


    ######################################################################################################################################################################

    # HABILITAR OU DESABILITAR USUÁRIOS

    # Todo comando abaixo é para alterar os status de cada usuário do MicroStrategy
    # Após a execução do comando de adição. Esse status se limita a true(Habilitado) ou false(Desabilitado)
    # Média de 3 minutos para executar
    logging.info("#####################################")
    logging.info("Alteração dos status dos usuários de acordo com a tabela do banco de dados")
    logging.info("#####################################")

    # Variável que armazena todos os CPFS todos usuários do Banco de dados
    for status_usuario_teradata in teradata_status_usuarios:
        
        # Variável que armazena todos as informações(ID, nome, CPF) dos usuários do Microstrategy
        for usuario_microstrategy_full in usuarios_mstr:
        
            # Verifica se os CPFS dos usuários do Teradata, são iguais aos CPFs dos usuários do MicroStrategy
            if status_usuario_teradata[0] == usuario_microstrategy_full['abbreviation']:
            
                # Formato do comando de alteração de status dos usuários do MicroStrategy, de acordo com o REST API  
                json_data_alter = {
                    'operationList': [
                            {
                                'op': 'replace',
                                'path': '/enabled',
                                # O comando Value para esta alteração, aceita apenas TRUE ou FALSE. Por isso, foi necessário utilizar uma função do Python para retornar true ou false. As listas retornam a informação entre '', o que não é aceito no comando para alteração de usuários da REST API do MicroStrategy.
                                'value': True if 'true' == status_usuario_teradata[1] else False
                            },
                        ],
                    }

                # Variável que armazena todas as informações do resultado da execução do REST API de alterações de status dos usuários MicroStrategy.
                status_alteracao_usuario = client_session.patch('http://10.14.203.158:8080/SEFADEVLIB/api/users/'+usuario_microstrategy_full['id'], headers=new_header, json=json_data_alter)
                stts_json = status_alteracao_usuario.json()
                
                id_usuario_alterado = "Usuário: " + str(stts_json['abbreviation'])
                status_usuario_alterado = "Status Habilitado: " + str(stts_json['enabled'])
                
                logging.info((id_usuario_alterado,status_usuario_alterado))
                
    logging.info("#####################################")
    logging.info("Script executado com sucesso!!!")
    logging.info("#####################################")

    ########################################################################################################################################################################

if __name__ == '__main__':
    main()











