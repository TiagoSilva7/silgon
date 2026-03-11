# ler arquivo xlsx e carregar em tabela no teradata
# se a tabela existir, ela sera dropada e recriada

import teradataml
from teradataml import create_context, remove_context, fastload
import pandas as pd
import os
from datetime import datetime, timedelta
import json
import requests
import teradata
from io import BytesIO


def load_parametros():
        # dir_atual = os.getcwd()
        # arq_param= os.path.join(dir_atual, 'pfe_params.json')
        arq_param="/home/pwc/etl_tdata/scripts/PFE/pfe_params.json"
    
        with open(arq_param) as f:
            var = json.load(f)
            return var

def download_file(url, filename):
    
    response = requests.get(url)
        
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"File downloaded successfully and saved as {filename}")
    else:
        print(f"Failed to download file. HTTP status code: {response.status_code}")

def download_file(url) -> BytesIO:
    """Realiza o download de um arquivo e retorna o conteudo em memoria, para analises sem necessidade de salvar o arquivo em disco.

    PARAMETRO
        url:
            Endereco para download do arquivo

    RETORNO
        io.BytesIO
            
    EXEMPLO
        1. Dowload arquivo excel

            >>> from io import BytesIO
            >>> url = "url-para-download.xlsx"
            >>> data = download_file(url)
            >>> df = pd.read_excel(data)
    """

    # fileurl = 'http://bi.sefa.parana:8080/CUBOSMSTR/igf-pfe.xlsx'
    try:
        response = requests.get(url)
        response.raise_for_status()
            
        if response.status_code == 200:
            content = BytesIO(response.content)
            return content
            # print("Arquivo obtido com sucesso")
        # else:
        #     print(f"Erro ao baixar o arquivo. HTTP status code: {response.status_code}")
    except Exception as err:
        raise SystemExit(err)

def print_logging(tipo, *args):
    data_log = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(data_log + ": " + tipo, *args)

def print_info(*args):
    print_logging("INFO", *args)

def print_erro(*args):
    print_logging("ERROR", *args)

def main():

    global json_var
    json_var=load_parametros()

    print (' >>>>>>> INICIO - DOWNLOAD ARQUIVO EXCEL -- DIRETORIO http://bi.sefa.parana:8080/CUBOSMSTR/igf-pfe.xlsx')

    # download do arquivo
    file_url = 'http://bi.sefa.parana:8080/CUBOSMSTR/igf-pfe.xlsx'
    local_filename = 'igf-pfe.xlsx'

    # download_file(file_url, local_filename)
    ARQUIVO = download_file(file_url)

    # ARQUIVO = '/home/pwc/etl_tdata/scripts/PFE/igf-pfe.xlsx'

    print (' >>>>>>> DOWNLOAD CONCLUIDO COM SUCESSO')
    #######################################################################################
    # CARREGA A TABELA DE DRR DO EXCEL ( ABA DRR )
    #######################################################################################
    print (' >>>>>>> CARREGA A TABELA DE DRR DO EXCEL ( ABA DRR ) -- NOME DA TABELA STG_PFE_DRR')
    
    df = pd.read_excel(ARQUIVO, sheet_name='DRR', engine='openpyxl', names=['CD_DRR','DS_RESUM_DRR','DS_DRR'])
    #df = pd.read_excel(r'C:\Users\tg186031\Downloads\AGAA\igf-pfe.xlsx', sheet_name='DRR', names=['CD_DRR','DS_RESUM_DRR','DS_DRR'])
    df = df.astype(str)
    
    param = {
        "TD_HOST":json_var["TD_HOST"],
        "TD_USER":json_var["TD_USER"],
        "TD_PWD":json_var["TD_PWD"],
        "TD_AMB":json_var["TD_AMB"]
    }

    con = create_context(host=param["TD_HOST"], username=param["TD_USER"], password=param["TD_PWD"])
    
    #######################################################################################
    # LIMPANDO TABELAS STAGES
    #######################################################################################
    print (' >>>>>>> LIMPANDO TABELAS STAGES')
    with con.begin() as conn:
        conn.execute(f"DELETE FROM {param['TD_AMB']}_STGDB.STG_PFE_DRR")
        conn.execute(f"DELETE FROM {param['TD_AMB']}_STGDB.STG_PFE")
        conn.execute(f"DELETE FROM {param['TD_AMB']}_STGDB.STG_PFE_AF")
        conn.close()

    # trocar o if_exists pra append se nao for recriar a tabela
    teradataml.copy_to_sql(df, table_name="STG_PFE_DRR", schema_name=f"{param['TD_AMB']}_STGDB")#, if_exists='replace')#, types={'DS_PFE':VARCHAR(1000),'DT_INI_PFE':VARCHAR(1000),'DT_FINAL_PFE':VARCHAR(1000),'DS_ORIG':VARCHAR(1000),'CD_IDENT':VARCHAR(1000),'DRR_CAD':VARCHAR(1000),'NU_PROTO':VARCHAR(1000),'NU_CNPJ_PFE':VARCHAR(1000),'DS_UF_PFE':VARCHAR(1000),'NM_CONTRIB':VARCHAR(1000),'VL_ESTIM':VARCHAR(1000),'NU_ANO_DECAD':VARCHAR(1000),'DS_ANO_MES_DECAD':VARCHAR(1000)	,'DT_INCL':VARCHAR(1000),'CD_DRR_CONTRIB':VARCHAR(1000),'CD_DRR_EXEC':VARCHAR(1000),'QT_PRAZO':VARCHAR(1000),'DS_PVF_DEN_IND':VARCHAR(1000),'IN_CNPJ_PFE':VARCHAR(1000)} )

    print (' >>>>>>> TABELA STG_PFE_DRR CARREGADA COM SUCESSO')

    #######################################################################################
    # CARREGA A TABELA FATO PFE DO EXCEL ( ABA PFE_AnexoVI )
    #######################################################################################
    print (' >>>>>>> CARREGA A TABELA FATO PFE DO EXCEL ( ABA PFE_AnexoVI ) -- NOME DA TABELA STG_PFE')
    
    df = pd.read_excel(ARQUIVO, sheet_name='PFE_AnexoVI', engine='openpyxl') #, names=['DS_PFE','DT_INI_PFE','DT_FINAL_PFE','DS_ORIG','CD_IDENT','DRR_CAD','NU_PROTO','NU_CNPJ_PFE','DS_UF_PFE','NM_CONTRIB','VL_ESTIM','NU_ANO_DECAD','DS_ANO_MES_DECAD','DT_INCL','CD_DRR_CONTRIB','CD_DRR_EXEC','QT_PRAZO','DS_PVF_DEN_IND','IN_CNPJ_PFE'])
    df = pd.read_excel(ARQUIVO, sheet_name='PFE_AnexoVI', engine='openpyxl', usecols='A:S')
    df = df.fillna('')
    df.rename(columns={'PFE':'DS_PFE','Data Inicial PFE':'DT_INI_PFE','Data Final PFE':'DT_FINAL_PFE','Origem':'DS_ORIG','Ident':'CD_IDENT','DRR Cadastro':'DRR_CAD','Protocolo':'NU_PROTO','CNPJ':'NU_CNPJ_PFE','UF':'DS_UF_PFE','NOME DO CONTRIBUINTE':'NM_CONTRIB','Vlr_Estimado':'VL_ESTIM','Ano_Decadencia':'NU_ANO_DECAD','Mes_Ano_Decadencia':'DS_ANO_MES_DECAD','Data_Inclusão':'DT_INCL','DRR_Contrib':'CD_DRR_CONTRIB','DRR_Execução':'CD_DRR_EXEC','Prazo':'QT_PRAZO','PVF/Den/Ind.':'DS_PVF_DEN_IND','FLAG_FALSO_POSITIVO':'IN_CNPJ_PFE'}, inplace=True)
    
    df = df.astype(str)
    
    df.replace("\u2013", '-', inplace=True, regex=True)
    df.replace("ª", 'º', inplace=True, regex=True)

    # trocar o if_exists pra append se nao for recriar a tabela
    teradataml.copy_to_sql(df, table_name="STG_PFE", schema_name=f"{param['TD_AMB']}_STGDB")#, if_exists='replace')#, types={'DS_PFE':VARCHAR(1000),'DT_INI_PFE':VARCHAR(1000),'DT_FINAL_PFE':VARCHAR(1000),'DS_ORIG':VARCHAR(1000),'CD_IDENT':VARCHAR(1000),'DRR_CAD':VARCHAR(1000),'NU_PROTO':VARCHAR(1000),'NU_CNPJ_PFE':VARCHAR(1000),'DS_UF_PFE':VARCHAR(1000),'NM_CONTRIB':VARCHAR(1000),'VL_ESTIM':VARCHAR(1000),'NU_ANO_DECAD':VARCHAR(1000),'DS_ANO_MES_DECAD':VARCHAR(1000)	,'DT_INCL':VARCHAR(1000),'CD_DRR_CONTRIB':VARCHAR(1000),'CD_DRR_EXEC':VARCHAR(1000),'QT_PRAZO':VARCHAR(1000),'DS_PVF_DEN_IND':VARCHAR(1000),'IN_CNPJ_PFE':VARCHAR(1000)} )

    print (' >>>>>>> TABELA STG_PFE CARREGADA COM SUCESSO')

    #######################################################################################
    # CARREGA A QUANTIDADE DE AUDITORES POR PFE ( ABA Auditores disponiveis )
    #######################################################################################
    print (' >>> CARREGA A QUANTIDADE DE AUDITORES POR PFE ( ABA Auditores disponiveis ) -- NOME DA TABELA STG_PFE_AF')
    df = pd.read_excel(ARQUIVO, sheet_name='Auditores disponiveis', engine='openpyxl', names=['DS_PFE','UN_DRR','QT_AF'])
    df = df.astype(str)
  
    # trocar o if_exists pra append se nao for recriar a tabela
    teradataml.copy_to_sql(df, table_name="STG_PFE_AF", schema_name=f"{param['TD_AMB']}_STGDB")#, if_exists='replace')#, types={'DS_PFE':VARCHAR(1000),'DT_INI_PFE':VARCHAR(1000),'DT_FINAL_PFE':VARCHAR(1000),'DS_ORIG':VARCHAR(1000),'CD_IDENT':VARCHAR(1000),'DRR_CAD':VARCHAR(1000),'NU_PROTO':VARCHAR(1000),'NU_CNPJ_PFE':VARCHAR(1000),'DS_UF_PFE':VARCHAR(1000),'NM_CONTRIB':VARCHAR(1000),'VL_ESTIM':VARCHAR(1000),'NU_ANO_DECAD':VARCHAR(1000),'DS_ANO_MES_DECAD':VARCHAR(1000)	,'DT_INCL':VARCHAR(1000),'CD_DRR_CONTRIB':VARCHAR(1000),'CD_DRR_EXEC':VARCHAR(1000),'QT_PRAZO':VARCHAR(1000),'DS_PVF_DEN_IND':VARCHAR(1000),'IN_CNPJ_PFE':VARCHAR(1000)} )

    print (' >>>>>>> TABELA STG_PFE_AF CARREGADA COM SUCESSO')

    print (' >>>>>>> PROCESSO FINALIZADO COM SUCESSO')

    remove_context()

if __name__ == '__main__':
    main()
    # print(load_parametros())
 