# Script em Python
# Versão 1.0 (V1.0)

# O tempo total de execução está entre 04 / 06 Minutos

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

    url_rest_api = 'http://10.14.203.158:8080/SEFADEVLIB/api/'

    #url_rest_api_prod = 'http://10.14.203.158:8080/SEFAPRODLIB_TESTE/api/'

    dt_inicio = datetime.now()

    print_info("#####################################")
    print_info("Status de conexão com as tabelas grupos de usuários e status de usuários")
    print_info("#####################################")

    udaExec = teradata.UdaExec(appName="RPR", version="1.0", logConsole=False, logLevel="ERROR")
    with udaExec.connect(
        method="odbc", \
        charset="UTF8", \
        system=json_var["TD_HOST"], \
        username=json_var["TD_USER"], \
        password=json_var["TD_PWD"], \
        driver="Teradata Database ODBC Driver 17.10", \
        SSLMode="Disable") as session:
                                         											
        # Conexão com o Teradata para buscar as informações do grupo de usuários e CPF dos usuários que pertencem a cada grupo.
        teradata_table = pd.read_sql("""SELECT DISTINCT 
                                            A.CD_GRUPO_RPR, 
                                            A.NU_CPF_USUAR_RPR 
                                            FROM
                                                (SELECT  	
                                                    LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0') AS NU_CPF_USUAR_RPR,
                                                    LPAD(CAST(SUR.CD_GRUPO_RPR as VARCHAR(3)), 3, '0') as CD_GRUPO_RPR,
                                                    GUR.NM_GRUPO_RPR,
                                                    SUR.DS_STATUS_USUAR_RPR,
                                                    CASE WHEN SUR.DS_STATUS_USUAR_RPR = 'ENABLED' THEN 'true' ELSE 'false' END AS DS_STATUS_PYTHON 
                                                FROM
                                                    $DB$_TGTDB.ERL_STATUS_USUAR_RPR SUR
                                                    JOIN $DB$_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR
                                                        ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR) 
                                                ) A""".replace("$DB$", json_var["TD_AMB"]), session)

        
        # Conexão com o Teradata para buscar os status de cada usuário a serem modificados no MicroStrategy
        teradata_stts_users = pd.read_sql("""SELECT DISTINCT 
                                                LPAD(CAST(SUR.NU_CPF_USUAR_RPR as VARCHAR(11)), 11, '0') AS NU_CPF_USUAR_RPR,
                                                CASE WHEN SUR.DS_STATUS_USUAR_RPR = 'ENABLED' THEN 'true' ELSE 'false' END AS DS_STATUS_PYTHON
                                                FROM
                                                    $DB$_TGTDB.ERL_STATUS_USUAR_RPR SUR
                                                    JOIN $DB$_TGTDB.ERL_TR_GRUPO_USUAR_RPR GUR
                                                        ON (SUR.CD_GRUPO_RPR = GUR.CD_GRUPO_RPR)""".replace("$DB$", json_var["TD_AMB"]), session)   
        
        # Conexão com o Teradata para selecionar apenas os CFS com os status abaixo, afim de , desativar os usuários listados.
        stts_recursos_humanos = pd.read_sql("""SELECT 
                                                LPAD(CAST(RHF.NU_CPF as VARCHAR(11)), 11, '0') AS NU_CPF,
                                                RHF.CD_SIT_FUNC,
                                                RHSF.DS_SIT_FUNC 
                                                FROM 
                                                    $DB$_ACCDB.DIM_RH_FUNC RHF 
                                                    JOIN $DB$_ACCDB.DIM_RH_SIT_FUNC RHSF 
                                                        ON (RHF.CD_SIT_FUNC = RHSF.CD_SIT_FUNC)
                                                WHERE RHSF.CD_SIT_FUNC in (2, 3, 4, 5, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 33, 34, 35)""".replace("$DB$", json_var["TD_AMB"]), session)


    print_info("Conexão realizada com sucesso nas tabelas grupos de usuários e status de usuários")            

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

    print_info("#####################################")
    print_info("Códigos dos grupos da tabela do banco de dados")
    print_info("#####################################")

    print_info(cd_grupos_teradata)

    teradata_cpf_unico_teradata = teradata_cd_group['NU_CPF_USUAR_RPR']

    cpf_usuario_teradata = []
    for elements in teradata_cpf_unico_teradata:
        if elements not in cpf_usuario_teradata:
            cpf_usuario_teradata.append(elements)

    cpf_usuario_teradata.sort()

    print_info("#####################################")
    print_info("Números de CPF dos usuários da tabela do banco de dados")
    print_info("#####################################")

    #print(type(cpf_usuario_teradata)) - list
    print_info(cpf_usuario_teradata)
    
    # Variável que converte a variável dos status dos usuários, cujo o type era DataFrame, em um objeto do tipo lista.
    teradata_status_usuarios = teradata_stts_users.values.tolist()

    # Variável que converte a variavel dos status dos usuários do RH em um objto do tipo lista
    stts_rh = stts_recursos_humanos.values.tolist()

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
    response = client_session.post(url_rest_api + 'auth/login', headers=headers, json=json_data)
    # Variável responsável por fazer a autenticação no REST API. Essa variável gera o TOKEN a ser utilizado ao longo do script - Produção
    #response = client_session.post(url_rest_api_prod + 'auth/login', headers=headers, json=json_data)

    # Variável responsável por guardar o TOKEN gerado anteriormente
    new_header = { 'X-MSTR-AuthToken': response.headers['X-MSTR-AuthToken'],
                'Accept': 'application/json', 
                'Content-Type': 'application/json',
        }

    ## Variável que pega os nomes e ids dos grupos de usuários - Desenvolvimento
    mstr_group_ids_names = client_session.get(url_rest_api + 'usergroups', params=group_params, headers=new_header)

    # Variável que pega os nomes e ids dos grupos de usuários - Produção
    #mstr_group_ids_names = client_session.get(url_rest_api_prod + 'usergroups', params=group_params, headers=new_header)

    # Variável que lista todos os grupos de usuários e seus IDs
    mstr_group_names = mstr_group_ids_names.json()

    ## Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON) - Desenvolvimento
    todos_usuarios_mstr = client_session.get(url_rest_api + 'users', params=users_params, headers=new_header)
   
    # Lista de todos os usuários que vem do MicroStrategy. Foi necessário transformar o type GET para JSON. Só assim, seria possível, filtrar as "colunas" dentro do objeto transformado(JSON) - Produção
    #todos_usuarios_mstr = client_session.get(url_rest_api_prod + 'users', params=users_params, headers=new_header)
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

    print_info("#####################################")
    print_info("IDs de todos os grupos do Microstrategy que tem o mesmo código de grupo do Banco de Dados")
    print_info("#####################################")

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

    print_info(ids_unicos_grupos)

    sair
    ######################################################################################################################################################################

    # REMOVE USUÁRIOS DOS GRUPOS

    # Todo comando abaixo, é para deletar todos os usuários de todos os grupos.
    # Média de 6 minutos para executar

    print_info("#####################################")
    print_info("Nome dos grupos do MicroStrategy e membros(usuários) retirados")
    print_info("#####################################")

    # Variável que faz um looping em todos os ids dos grupos, pegando os usuários que pertecem a cada grupo.
    # Cria uma lista com todos os ids de usuários pertencentes a cada grupo, e passando esses ids, como parâmetros para o comando de removendo todos esses usuários de todos os grupos.
    for id_grupos_deleta_usuarios_mstr in mstr_groups_ids:
        #print(id_grupos_deleta_usuarios_mstr)

        #Desenvolvimento
        users_ids_response = client_session.get(url_rest_api + 'usergroups/'+id_grupos_deleta_usuarios_mstr+'/members', params=users_params, headers=new_header)

        #Produção
        #users_ids_response = client_session.get(url_rest_api_prod + 'usergroups/'+id_grupos_deleta_usuarios_mstr+'/members', params=users_params, headers=new_header)
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
        
        # # Variável que armazena todas as informações do resultado da execução do REST API de retirada de cada usuário de cada grupo do MicroStrategy. - Desenvolvimento
        remove_usuarios_mstr = client_session.patch(url_rest_api + 'usergroups/'+id_grupos_deleta_usuarios_mstr, headers=new_header, json=json_data_remove)    
         
        # Variável que armazena todas as informações do resultado da execução do REST API de retirada de cada usuário de cada grupo do MicroStrategy. - Produção
        #remove_usuarios_mstr = client_session.patch(url_rest_api_prod + 'usergroups/'+id_grupos_deleta_usuarios_mstr, headers=new_header, json=json_data_remove)    
        status_remove_usuarios = remove_usuarios_mstr.json()
        

        # Variáveis apenas das informações para serem adicionadas no LOG
        nm_grupo_removido = "Grupo: " + status_remove_usuarios['abbreviation']
        id_membros_removido = "Membros Removidos: " + str(users_complete)

        print_info((nm_grupo_removido,id_membros_removido))
    

    ######################################################################################################################################################################

    # ADICIONAR USUÁRIOS

    # Todo comando abaixo é para buscar os usuários dentro do banco de dados, posteriormente buscar os ids deles dentro do MicroStrategy 
    # Por fim, adicionar cada um deles, nos grupos oriundos do banco de dados
    # Média de 4 minutos para executar

    print_info("#####################################")
    print_info("Adiciona somente os usuários que estão na tabela do banco de dados")
    print_info("#####################################")

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
    
        # Verifica se não existe grupo para ser adicionado, ou seja, a lista tá vazia.
        if not grupo_a_ser_adicionado: 
            continue

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
        
        # # Variável que armazena todas as informações do resultado da execução do REST API de adição de usuários dentro de cada grupo do MicroStrategy. - Desenvolvimento
        status_adicao = client_session.patch(url_rest_api + 'usergroups/'+grupo_a_ser_adicionado, headers=new_header, json=json_data_add)     
        
        # Variável que armazena todas as informações do resultado da execução do REST API de adição de usuários dentro de cada grupo do MicroStrategy. - Produção
        #status_adicao = client_session.patch(url_rest_api_prod + 'usergroups/'+grupo_a_ser_adicionado, headers=new_header, json=json_data_add)     
        status_adicao_json = status_adicao.json()

        # Verifica se existe erros na inserção de usuários dentro dos grupos
        if 'code' in status_adicao_json:
            id_membros_error = "Membros com erro: " + str(list(usuario_a_Ser_Adicionado))
            print_erro((status_adicao_json, id_membros_error))
        else:
            nm_grupo_add = "Grupo: " + str(status_adicao_json['abbreviation'])
            id_membros_add = "Membros adicionados: " + str(list(usuario_a_Ser_Adicionado))
            print_info((nm_grupo_add, id_membros_add)) 


    ######################################################################################################################################################################

    # HABILITAR OU DESABILITAR USUÁRIOS

    # Todo comando abaixo é para alterar os status de cada usuário do MicroStrategy
    # Após a execução do comando de adição. Esse status se limita a true(Habilitado) ou false(Desabilitado)
    # Média de 3 minutos para executar
    print_info("#####################################")
    print_info("Alteração dos status dos usuários de acordo com a tabela do banco de dados")
    print_info("#####################################")

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

                # # Variável que armazena todas as informações do resultado da execução do REST API de alterações de status dos usuários MicroStrategy. - Desenvolvimento
                status_alteracao_usuario = client_session.patch(url_rest_api + 'users/'+usuario_microstrategy_full['id'], headers=new_header, json=json_data_alter)
                                
                # Variável que armazena todas as informações do resultado da execução do REST API de alterações de status dos usuários MicroStrategy. - Produção
                #status_alteracao_usuario = client_session.patch(url_rest_api_prod + 'users/'+usuario_microstrategy_full['id'], headers=new_header, json=json_data_alter)
                stts_json = status_alteracao_usuario.json()
                
                id_usuario_alterado = "Usuário: " + str(stts_json['abbreviation'])
                status_usuario_alterado = "Status Habilitado: " + str(stts_json['enabled'])
                
                print_info((id_usuario_alterado,status_usuario_alterado))

    
                
    ######################################################################################################################################################################

    # DESABILITAR USUÁRIOS QUE NÃO TEM GRUPO, APENAS O GRUPO EVERYONE.

    print_info("#####################################")
    print_info("Alteração dos status dos usuários sem grupos no Receita PR e apenas com o Grupo Everyone no MicroStrategy")
    print_info("#####################################")
    
    # Variável que armazena os usuários sem grupos do microstrategy
    usuarios_desativar = []
    
    # Loop para gerar a lista de usuários únicos, sem grupo dentro do MicroStrategy a serem desativados.
    for desativa_usuarios_sem_grupo in lista_id_usuarios_mstr:
        #Desenvolvimento
        usuarios_grupo_mstr_all = client_session.get(url_rest_api + 'users/'+desativa_usuarios_sem_grupo, params=users_params_groups, headers=new_header)
        #Produção
        #usuarios_grupo_mstr_all = client_session.get(url_rest_api_prod + 'users/'+desativa_usuarios_sem_grupo, params=users_params_groups, headers=new_header)
        
        # Variável que armazena a conversão de um response para um dicionário python
        converte_usuarios_para_lista = usuarios_grupo_mstr_all.json()
        
        # variável que armazena uma lista convertida do dicionário acima
        lista_usuarios_convertidos = [i for i in converte_usuarios_para_lista.values()]
     
        # Verificação se o usuário tem somente um grupo, e se esse grupo é o Everyone. Se for verdadeiro, armazena o ID do usuário dentro da variável "usuarios_desativar"
        if len(lista_usuarios_convertidos[1]) == 1:
            if lista_usuarios_convertidos[1][0]['name'] == 'Everyone':
                usuarios_desativar.append(lista_usuarios_convertidos[0])

    # Loop que verifica cada usuário armazenado na variável "usuarios_desativar", desativando em sequencia
    for usuarios_desativar_sem_grupo in usuarios_desativar:
            
        json_data_alter_sem_grupo = {
                        'operationList': [
                                {
                                    'op': 'replace',
                                    'path': '/enabled',
                                    # O comando Value para esta alteração, aceita apenas TRUE ou FALSE. Como vamos desativar os usuários sem grupos, o Default é FALSE.
                                    'value': False
                                },
                            ],
                        }

        # Variável que armazena todas as informações do resultado da execução do REST API de alterações de status dos usuários sem grupos do MicroStrategy.
        #Desenvolvimento
        status_alteracao_usuario_sem_grupo = client_session.patch(url_rest_api + 'users/'+usuarios_desativar_sem_grupo, headers=new_header, json=json_data_alter_sem_grupo)
        #Produção
        #status_alteracao_usuario_sem_grupo = client_session.patch(url_rest_api_prod + 'users/'+usuarios_desativar_sem_grupo, headers=new_header, json=json_data_alter_sem_grupo)
        stts_alteraca_sem_grupo = status_alteracao_usuario_sem_grupo.json()
                    
        id_usuario_alterado_sem_grupo = "Usuário: " + str(stts_alteraca_sem_grupo['abbreviation'])
        status_usuario_alterado_sem_grupo = "Status Habilitado: " + str(stts_alteraca_sem_grupo['enabled'])

        print_info((id_usuario_alterado_sem_grupo, status_usuario_alterado_sem_grupo))

    #####################################################################################################################################################################

    # DESABILITA USUÁRIOS COM A SITUAÇÃO NO RH DE ACORDO COM OS CÓDIGOS ABAIXO
    # 2, 3, 4, 5, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 33, 34, 35 

    print_info("#####################################")
    print_info("Desativação de usuários no MicroStratey, com Status diferente de ATIVO no RH.")
    print_info("#####################################")
    
    params_status_usuario_microstrategy = {
        'fields': 'id,abbreviation,enabled',
        }

    usuario_ativo_microstrategy = []

    for usuario_mstr_ativo in lista_id_usuarios_mstr:
        #Desenv
        status_usuario_ativo_mstr = client_session.get(url_rest_api + 'users/' + usuario_mstr_ativo , params=params_status_usuario_microstrategy, headers=new_header)
        #prod
        #status_usuario_ativo_mstr = client_session.get(url_rest_api_prod + 'users/' + usuario_mstr_ativo , params=params_status_usuario_microstrategy, headers=new_header)
        var_status_usuario_ativo_mstr = status_usuario_ativo_mstr.json()
        if var_status_usuario_ativo_mstr['enabled'] == True:
            usuario_ativo_microstrategy.append(var_status_usuario_ativo_mstr)
    
    #print(usuario_ativo_microstrategy)
                
    print_info("#####################################")
    print_info("Relação de usuários do RH, com status diferente de ativo, pré definidos anteriormente, para desativação ")
    print_info("#####################################")

    usuarios_status_desativar = []
    
    for status_rh in stts_rh:
         #print(status_rh)
        usuarios_status_desativar.append((status_rh[0],status_rh[2]))
       
    print_info(usuarios_status_desativar)    

    print_info("#####################################")
    print_info("Relação dos usuários ativos no MicroStrategy que foram desativados.")
    print_info("#####################################")
    
    #lista_microstrategy_completa = []

    for lista_completa_mstr_desativar in usuario_ativo_microstrategy:
        for status_rh in stts_rh:
            if lista_completa_mstr_desativar['abbreviation'] in status_rh[0]:
            
                #Desenv
                status_usuario_desativado_mstr = client_session.patch(url_rest_api + 'users/'+ lista_completa_mstr_desativar['id'], headers=new_header, json=json_data_alter_sem_grupo)
                #Prod
                #status_usuario_desativado_mstr = client_session.patch(url_rest_api_prod + 'users/'+ lista_completa_mstr_desativar['id'], headers=new_header, json=json_data_alter_sem_grupo)
                var_status_usuario_desativado_mstr = status_usuario_desativado_mstr.json()
                #lista_microstrategy_completa.append(lista_completa_mstr_desativar['id'])
                
                cpf_usuario_desativado = "Usuário: " + str(var_status_usuario_desativado_mstr['abbreviation'])
                status_usuario_desativado_rh = "Situação da Desativação: " + str(status_rh[2])    
                
                print_info((cpf_usuario_desativado, status_usuario_desativado_rh))
                break
        
  
    dt_fim = datetime.now()
    dt_total = str(dt_fim - dt_inicio)

    print_info("#####################################")
    print_info("Script executado com sucesso!!!")
    print_info("Tempo de execução: " + dt_total)
    print_info("#####################################")

    ########################################################################################################################################################################

if __name__ == '__main__':
    main()











