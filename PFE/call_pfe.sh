#!/bin/bash

export ODBCINST=/opt/teradata/client/ODBC_64/odbcinst.ini

data=$(date +"%Y%m%d%H%M%S")
V_ARQ_LOG=/home/pwc/etl_tdata/log/PFE/PFE_$data.log
RC=0

#Chamada do Python
python -W ignore /home/pwc/etl_tdata/scripts/PFE/pfe_import_excel_file_dw.py >> $V_ARQ_LOG 2>&1
RC=$?

# Verificar existencia de arquivo de log preenchido

if [ -s $V_ARQ_LOG ] && [ $RC -eq 0 ]; then
        find /home/pwc/etl_tdata/log/RPR -name "*.log" -type f -mtime +180 -delete
        exit 0
else
        echo "Possível carga interrompida durante leitura na origem. Necessário retomada manual." >> $V_ARQ_LOG
        exit 1
fi

