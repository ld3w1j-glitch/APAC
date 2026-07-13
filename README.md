# APAC Visitas V3

Sistema de Gestão de Visitas da APAC de Pouso Alegre - MG.

## Novidades da V3

- Correção definitiva da logo, com “POUSO ALEGRE - MG” totalmente visível.
- Painel administrativo separado do painel do usuário/visitante.
- Novo Portal do Visitante em página longa, responsiva e guiada.
- História e propósito institucional.
- Botões de navegação que levam diretamente a cada orientação.
- Conteúdo organizado na mesma sequência do vídeo institucional:
  1. Cadastro e documentação
  2. Documentos exigidos
  3. Quem pode visitar
  4. Uso da credencial
  5. Horários
  6. Crianças e responsáveis
  7. Roupas permitidas
  8. Segurança
  9. Áreas restritas
  10. Durante a visita
  11. Condutas não permitidas
  12. Encerramento
- Imagens institucionais integradas ao portal.
- Perfil “Visitante / usuário institucional” disponível na gestão de usuários.
- Usuários do perfil visitante não acessam módulos administrativos.
- Relatório diário em PDF mantido.
- Compatível com Windows usando Python 3.12 e SQLite.
- Preparado para PostgreSQL e Railway.

## Acessos iniciais

### Administração
- Usuário: `admin`
- Senha: `admin123`

### Portal do visitante
- Usuário: `visitante`
- Senha: `visitante123`

Altere as credenciais antes do uso oficial.

## Executar no Windows

1. Instale o Python 3.12 de 64 bits.
2. Extraia o ZIP em uma pasta nova.
3. Execute `INICIAR_WINDOWS.bat`.
4. Acesse `http://127.0.0.1:5000`.

O iniciador recria automaticamente o ambiente virtual caso ele tenha sido criado com uma versão incompatível do Python.
