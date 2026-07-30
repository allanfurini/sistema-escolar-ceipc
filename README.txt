SISTEMA ESCOLAR CEIPC - VERSÃO 6.4

Correção urgente do Histórico Escolar sem perda de dados.

ALTERAÇÕES:
- os dados automáticos do ano atual continuam sempre visíveis no histórico;
- acrescentar ou editar anos anteriores não substitui o ano atual;
- salvar carga horária não apaga disciplinas, notas, anos ou matrículas;
- carga horária do ano atual pode ser registrada por componente curricular;
- campo opcional de carga horária anual;
- anos anteriores e outras escolas continuam em linhas manuais independentes;
- novas tabelas/colunas são criadas por migração segura, sem apagar o banco existente.

IMPORTANTE:
- mantenha o persistent disk do Render montado no mesmo caminho;
- faça um backup pelo sistema antes do deploy, como camada extra de segurança;
- esta atualização não recria as tabelas de alunos, notas, turmas ou matrículas.

VERSÃO 6.5
- Histórico escolar em grade oficial: componentes curriculares nas linhas.
- 1º ao 9º ano nas colunas, cada série com N/C e CH.
- Registros complementares separados por série, ano, escola, município e UF.
- Ano atual continua vindo automaticamente do Diário/Boletim.
- Upgrade preserva alunos, notas, turmas, matrículas e históricos anteriores.


CORREÇÃO V6.5.1
- Corrige erro 500 ao salvar o histórico escolar editável.
- Ajusta a quantidade de parâmetros do INSERT/UPDATE de historico_documentos.
- Não altera nem apaga alunos, notas, matrículas, turmas ou históricos existentes.


VERSÃO 6.5.2
- Remove do histórico impresso o quadro de matrícula com datas de início/fim.
- Remove o quadro separado de Educação Física.
- Mantém os dados antigos dessas tabelas preservados no banco.
- Amplia as áreas de observações e certificação no verso.
