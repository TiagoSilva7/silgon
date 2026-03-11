# pesquisar modulo de log

# Script em Python
# Versão 1.0 (V1.0)

# Para editar/executar o código abaixo, é necessário fazer o download de qualquer IDE. Para esta versão, foi utilizado a IDE chamada VSCode
# Após a instalação da IDE é necessário instalar alguns módulos que foram utilizados no programa.

# Importação de módulos
# Para instalar os módulos abaixo, basta entrar no CMD e digitar o seguinte comando pip install nome_do_modulo

import teradatasql
import pandas as pd
import requests
import json

# Conexão com o Teradata para buscar as informações dentro das tabelas dos grupos de usuários
with teradatasql.connect(host='10.14.203.21', user='tiago.silva', password='sefacre') as connect:
    teradata_table = pd.read_sql("select distinct cd_grupo, cpf_usuario from p_tmpdb.dim_usuarios_rpr", connect)

# Variável que armazena os códigos dos grupos e usuários de cada grupo recebidos pelo Receita PR. 
teradata_cd_group = (teradata_table)
#print(type(teradata_concat_group_name))

# Variável que converte a variável acima, cujo o type erada DataFrame, em um objeto do tipo lista.
teradata_codigo_grupo = teradata_cd_group.values.tolist()
#print(teradata_group_name)

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



##################################################################################

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
    
    # Variável que faz a remoção dos usuários do array acima.
    remove_usuarios_mstr = client_session.patch('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+id_grupos_deleta_usuarios_mstr, headers=new_header, json=json_data_remove)    
    

###################################################################


# ADICIONAR USUÁRIOS
# Todo comando abaixo é para buscar os usuários dentro do banco de dados, posteriormente buscar os ids deles dentro do MicroStrategy 
# Por fim, adicionar cada um deles, nos grupos oriundos do banco de dados
# Média de 6 minutos para executar

Lista_ids_grupos_users_td_mstr = []

for td_groups_users in teradata_codigo_grupo:
    #print(td_groups_users)
    id_group = ''
    id_user = ''
    for mstr_all_groups in mstr_group_names:
        #print(mstr_all_groups['name'].split('-')[0].strip())
        if mstr_all_groups['name'].split('-')[0].strip() == td_groups_users[0]:
           #print(mstr_all_groups['id'])
           #Lista_ids_grupos_users_td_mstr.append(mstr_all_groups['id'])
           id_group = mstr_all_groups['id']
    for mstr_users_list_all in usuarios_mstr:
        #print(mstr_users_list_all)
         if td_groups_users[1] == mstr_users_list_all['abbreviation']:
             #print(mstr_users_list_all['id'])
             id_user = mstr_users_list_all['id']
    #print(mstr_users_list_all)    
    Lista_ids_grupos_users_td_mstr.append((id_group, id_user))        
#print(Lista_ids_grupos_users_td_mstr)

usuarios_para_adicionar_no_mstr = {}

for linhas_distintas in Lista_ids_grupos_users_td_mstr:
    #print(linhas_distintas)
    id_group_lista, id_user_lista = linhas_distintas
    if id_group_lista not in usuarios_para_adicionar_no_mstr:
        usuarios_para_adicionar_no_mstr[id_group_lista] = set()
    usuarios_para_adicionar_no_mstr[id_group_lista].add(id_user_lista)
    #print(linhas_distintas)

for grupo_a_ser_adicionado, usuario_a_Ser_Adicionado in usuarios_para_adicionar_no_mstr.items():
    #print(grupo_a_ser_adicionado, usuario_a_Ser_Adicionado)    
    json_data_add = {
        "operationList": [
            {
                "op": "add",
                "path": "/members",
                "value": list(usuario_a_Ser_Adicionado),
            },
        ],
    }

    adiciona_usuarios_grupos = client_session.patch('http://10.14.203.158:8080/SEFADEVLIB/api/usergroups/'+grupo_a_ser_adicionado, headers=new_header, json=json_data_add)     
#print(Lista_ids_grupos_users_td_mstr)
#print(usuarios_para_adicionar_no_mstr)























