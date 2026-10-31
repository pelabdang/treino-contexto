#!/bin/bash
# Impede que uma tarefa seja concluída com testes falhando
cd "$CLAUDE_PROJECT_DIR" || exit 0
pytest -q > /tmp/pytest.log 2>&1; rc=$?
if [ $rc -ne 0 ] && [ $rc -ne 5 ]; then # 5 = nenhum teste encontrado
    echo "Testes do backend falhando. Corrija antes de concluir:" >&2
    tail -30 /tmp/pytest.log >&2
    exit 2
fi
if [ -f apps/mobile/package.json ]; then
    if ! npm test --prefix apps/mobile -- --watchAll=false > /tmp/jest.log 2>&1; then
        echo "Testes do app falhando. Corrija antes de concluir:" >&2
        tail -30 /tmp/jest.log >&2
        exit 2
    fi
fi
exit 0