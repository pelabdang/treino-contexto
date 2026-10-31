# Kit inicial do repositório treino-contexto

Copie TUDO desta pasta para a raiz do seu repositório (incluindo as pastas ocultas .claude/ e .github/).

Raiz do repositório depois de copiar:

    treino-contexto/
    ├── AGENTS.md                  regras do time (todos os agentes leem)
    ├── CLAUDE.md                  diz ao Claude Code para ler o AGENTS.md
    ├── .gitignore
    ├── .graphifyignore
    ├── .github/workflows/testes.yml   testes automáticos no GitHub
    ├── .claude/
    │   ├── settings.json          times de agentes, permissões e hook
    │   ├── hooks/testes.sh        impede concluir tarefa com teste quebrado
    │   └── agents/                um arquivo por agente
    └── docs/produto/plano-mvp-execucao.md

Depois:
    git add .
    git commit -m "Kit do time de agentes"
    git push

No macOS, pastas que começam com ponto ficam ocultas no Finder: aperte Cmd+Shift+. para mostrar.
O modo Auto vai em ~/.claude/settings.json (na sua pasta de usuário, não no repositório): veja o passo 5 do tutorial.
