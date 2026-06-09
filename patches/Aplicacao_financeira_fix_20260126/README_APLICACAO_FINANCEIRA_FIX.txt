Instruções para aplicar o patch — Aplicação Financeira

Arquivos incluídos:
- index.html
- script.js

Objetivo:
Corrigir exclusão de parcelas/recorrências e adicionar o tipo "PIX" no select de despesas.

Precauções (IMPORTANTE: não perca os lançamentos do usuário):
1) Fazer backup dos dados do usuário
   - Preferido (mais simples): abra a aplicação (Portable) -> Aba "Ferramentas" -> "Exportar backup (JSON)" e salve o arquivo em local seguro.
   - Alternativa (devs): abrir DevTools do navegador (F12) -> Application -> Local Storage -> selecione a origem da aplicação e exporte o valor da chave `controle_financeiro_lancamentos_v1`. Salve como JSON.

2) Backup da pasta portable
   - Antes de substituir arquivos, copie a pasta portable (ou a subpasta `app` conforme sua distribuição) para um local seguro.

Como aplicar o patch (versão portátil):
- Local da aplicação portable: encontre a pasta onde o usuário guarda os arquivos da aplicação (ex.: `Portable_ControleFinanceiro_2.3.2\app` ou a pasta usada para distribuir a versão portable).
- Substituir arquivos:
  1. Pare a aplicação / feche o navegador que esteja usando o app (garante que localStorage não seja sobrescrito durante substituição).
  2. Copie os arquivos `index.html` e `script.js` desta pasta (ou substitua diretamente) para a pasta `app` da versão portable, sobrescrevendo os arquivos existentes.
  3. Abra a aplicação novamente (index.html ou o executável portable).

Verificações pós-aplicação:
- Abrir a aba "Resumo Geral" e verificar se os lançamentos aparecem (mesmo saldo e registros do backup).
- Teste rápido: na aba "Lançamentos", tente excluir uma parcela de um parcelamento (se existir) e confirme que o grupo inteiro é removido.

Se algo der errado / restauração:
- Restaure a pasta portable a partir do backup da pasta que você fez antes da substituição.
- OU importe o backup JSON salvo via Ferramentas -> Importar backup (escolha modo "Substituir tudo" se quiser restaurar exatamente).

Observações técnicas:
- Os dados do usuário são salvos no Local Storage do navegador sob a chave `controle_financeiro_lancamentos_v1` e outras chaves auxiliares. Substituir apenas `index.html` e `script.js` não altera o Local Storage por si só — porém é essencial fazer backup antes.
- NÃO execute a URL de teste `?run_test=1` em uma instalação real sem backup, pois o teste limpa e regrava dados para validar o cenário.

Precisa que eu gere um ZIP com esses arquivos (pronto para enviar)?
- Responda "ZIP" e eu crio o ZIP e uma mensagem curta pronta para enviar ao usuário explicando os passos acima.

Assinatura: Gerado automaticamente por sua equipe de manutenção em 2026-01-26
