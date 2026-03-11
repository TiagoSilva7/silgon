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

# Conexão com o Teradata para buscar as informações dentro das tabelas dos grupos de usuários
with teradatasql.connect(host='10.14.203.21', user='tiago.silva', password='sefacre') as connect:
    teradata_table = pd.read_sql(" select distinct cd_grupo, cpf_usuario from p_tmpdb.dim_usuarios_rpr where cd_grupo is not null and trim(cd_grupo) not in ('null','###') and trim(cpf_usuario) <> '77777777777'", connect)

# Variável que armazena os códigos dos grupos e usuários de cada grupo recebidos pelo Receita PR. 
teradata_cd_group = (teradata_table)
#print(type(teradata_concat_group_name))

# Variável que converte a variável acima, cujo o type era DataFrame, em um objeto do tipo lista.
teradata_codigo_grupo = teradata_cd_group.values.tolist()
#print(teradata_group_name)

# Conexão com o Teradata para buscar os status de cada usuário a serem modificados no MicroStrategy
with teradatasql.connect(host='10.14.203.21', user='tiago.silva', password='sefacre') as connect:
    teradata_stts_users = pd.read_sql("select distinct cpf_usuario, stts_usuario_json from p_tmpdb.dim_usuarios_stts where trim(cpf_usuario) not in ('77777777777', '99999999999')", connect)
#print(type(teradata_stts_users))

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


# Variável que converte os dados da variável anterior em uma variável do tipo lista.
# Variável do tipo lista, permite fazer filtros
mstr_groups_ids = list(lista_id_mstr_groups)

######################################################################################################################################################################

# DELETE

# Todo comando abaixo, é para deletar todos os usuários de todos os grupos.
# Média de 6 minutos para executar

# Variável que faz um looping em todos os ids dos grupos, pegando os usuários que pertecem a cada grupo.
# Cria uma lista com todos os ids de usuários pertencentes a cada grupo, e passando esses ids, como parâmetros para o comando de removendo todos esses usuários de todos os grupos.

for id_grupos_deleta_usuarios_mstr in mstr_groups_ids:
    #print(obj)

    users_ids_response = client_session.get('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+id_grupos_deleta_usuarios_mstr+'/members', params=users_params, headers=new_header)
    users_id = users_ids_response.json()

    # Criação de um array de todos os ids dos usuários pertencentes a cada grupo.
    users_complete = []
    #print(users_id)

    # Loop que adiciona os IDs de cada usuário do MicroStrategy dentro do array criado acima
    for usmstr in users_id:
        users_complete.append(usmstr['id'])
    
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


######################################################################################################################################################################

# ADICIONAR USUÁRIOS

# Todo comando abaixo é para buscar os usuários dentro do banco de dados, posteriormente buscar os ids deles dentro do MicroStrategy 
# Por fim, adicionar cada um deles, nos grupos oriundos do banco de dados
# Média de 4 minutos para executar

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
            
    #print(linhas_distintas)

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


######################################################################################################################################################################

# HABILITAR OU DESABILITAR USUÁRIOS

# Todo comando abaixo é para alterar os status de cada usuário do MicroStrategy
# Após a execução do comando de adição. Esse status se limita a true(Habilitado) ou false(Desabilitado)
# Média de 3 minutos para executar

# Variável que armazena todos os CPFS todos usuários do Banco de dados
for status_usuario_teradata in teradata_status_usuarios:
    # print(status_usuario_teradata)
  
    # Variável que armazena todos as informações(ID, nome, CPF) dos usuários do Microstrategy
    for usuario_microstrategy_full in usuarios_mstr:
    #print(usuarios_microstrategy_full)

        # Verifica se os CPFS dos usuários do Teradata, são iguais aos CPFs dos usuários do MicroStrategy
        if status_usuario_teradata[0] == usuario_microstrategy_full['abbreviation']:
        #print(usuario_microstrategy_full['id'], status_usuario_teradata[1])
        

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
            #print(type(status_alteracao_usuario))



########################################################################################################################################################################












