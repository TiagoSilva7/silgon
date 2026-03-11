#!/bin/bash

export ODBCINST=/opt/teradata/client/ODBC_64/odbcinst.ini

#echo "ODBCINST" $ODBCINST
#echo "ODBCINI" $ODBCINI

data=$(date +"%Y%m%d%H%M%S")
V_ARQ_LOG=/home/pwc/etl_tdata/log/SCANC/SCANC_DOWNLOAD_ARQUIVOS_$data.log
RC=0

#Limpa a pasta dos arquivos

if [ ! -z "$(ls -A /home/pwc/etl_tdata/scripts/SCANC/download/entrada)" ]; then
	echo "Limpando a pasta entrada:" > $V_ARQ_LOG
        rm -r /home/pwc/etl_tdata/scripts/SCANC/download/entrada/* >> $V_ARQ_LOG 2>&1
else 
	echo "Pasta de entrada vazio." >> $V_ARQ_LOG
fi

#Chamada do Python
python -W ignore /home/pwc/etl_tdata/scripts/SCANC/download/scanc_download.py >> $V_ARQ_LOG 2>&1
RC=$?

#conta_xml="$(find . -type f -name \*.xml | wc -l)"

# Verificar existência de arquivo de log preenchido
#if [ -s $V_ARQ_LOG ] && [ $RC -eq 0 ] && [ $conta_xml -gt 0 ]; then
if [ -s $V_ARQ_LOG ] && [ $RC -eq 0 ]; then
        find /home/pwc/etl_tdata/log/SCANC -name "*.log" -type f -mtime +180 -delete
        exit 0
else
        echo "Possível carga interrompida durante leitura na origem. Necessário retomada manual." >> $V_ARQ_LOG
        exit 1
fi




