SISTEMA ESCOLAR CEIPC - VERSÃO 3

Novidades da v3:
- login e senha
- usuário administrador e secretaria
- edição completa do cadastro de alunos
- exclusão com confirmação dupla
- mudança de turma preservando histórico
- boletim anual com notas individuais, médias e faltas
- histórico escolar / transferência para impressão
- auditoria básica de alterações
- backup manual do banco
- migração segura para campos novos sem apagar dados antigos

Acesso inicial:
login: admin
senha: admin123

Observações:
- coloque a logo oficial da escola em static/logo-escola.png se quiser mostrar a imagem nos documentos
- o banco usa o persistent disk do Render quando a variável RENDER_DISK_PATH estiver disponível

VERSÃO 6.3 - HISTÓRICO ESCOLAR EDITÁVEL
- Todos os campos do histórico frente e verso podem ser preenchidos e salvos por aluno.
- Linhas de rendimento, carga horária, faltas e resultado são editáveis e expansíveis.
- Registros complementares e Educação Física também são editáveis.
- Os dados editáveis ficam em tabelas novas; alunos, matrículas, notas e boletins existentes não são apagados.
- O histórico impresso usa os dados manuais quando existirem e mantém o preenchimento automático como fallback.
