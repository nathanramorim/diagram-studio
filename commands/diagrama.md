---
description: Gera um diagrama técnico (SVG e PNG) a partir de uma descrição, código, ASCII ou README.
argument-hint: "[o que desenhar]"
---

Gere o diagrama seguindo a skill `diagrama-studio`.

- Pedido: `$ARGUMENTS` (vazio = pergunte o que desenhar).
- O script está em `${CLAUDE_PLUGIN_ROOT}/scripts/diagrama.py` e os exemplos em `${CLAUDE_PLUGIN_ROOT}/exemplos/`.
- Mostre o plano do desenho e espere a confirmação antes de gravar. Não faça commit.
