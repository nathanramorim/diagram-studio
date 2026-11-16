---
name: diagrama-studio
description: Use para desenhar diagramas técnicos (arquitetura, fluxo, decisões de arquitetura, antes e depois, camadas, personas, pipeline) em SVG e PNG, no estilo escuro com grade, setas em ângulo reto, texto que sempre cabe e assinatura com avatar no canto. Ative quando pedirem "diagrama", "desenha isso", "fluxo", "arquitetura", "ADR com imagem", "como as peças se conectam", ou colarem ASCII, README, spec ou código pedindo uma explicação visual.
---

# diagrama-studio

Transforma uma ideia técnica em uma imagem simples de entender. O desenho é descrito num JSON curto e o script cuida do estilo, da grade, das setas e da assinatura.

## Passo a passo

1. **Entenda o que contar.** Leia o pedido, o código, o README ou o ASCII. Responda para você mesmo: qual é a mensagem em uma frase? Essa frase vira o `titulo`.
2. **Escolha o modelo** (veja `exemplos/`):
   | Modelo | Quando usar | Exemplo |
   |---|---|---|
   | Fases | migração, evolução, antes e depois | `exemplos/estrangulamento.json` |
   | Personas | quem usa o quê, isolamento, permissões | `exemplos/personas.json` |
   | Fluxo | passo a passo, pipeline, requisição | combine `caixa` + `seta` em linha |
   | Camadas | frontend, API, dados, infra | caixas largas empilhadas com setas verticais |
3. **Assinatura.** Se não existir `~/.config/diagram-studio/assinatura.json`, avise uma vez que o padrão é a assinatura do autor do plugin e pergunte se a pessoa quer manter, usar a dela (nome, GitHub, link e foto opcional) ou gerar sem assinatura. Grave a escolha nesse arquivo para não perguntar de novo.
4. **Mostre o plano** em até 5 linhas (título, blocos principais, setas) e espere o "sim".
5. **Escreva o JSON** em `docs/diagramas/<nome>.json` (ou onde o usuário pedir).
6. **Gere:** `uv run <plugin>/scripts/diagrama.py docs/diagramas/<nome>.json`
   Sai `<nome>.svg` e `<nome>.png` ao lado do JSON. Use `--saida caminho/sem-extensao` para outro lugar.
7. **Confira o PNG** (abra a imagem). Corrija texto apertado (o script avisa), setas cruzando caixas ou blocos desalinhados. Repita até ficar limpo.
8. **Entregue** o SVG para README e docs, e o PNG para slides, LinkedIn e chat.

## Regras de desenho

- **Uma mensagem por diagrama.** Se precisar de duas, faça dois.
- **Poucas palavras.** Caixas com 1 a 3 palavras; detalhe vai no `sub` ou numa `nota`.
- **Grade de 8 px.** Use x, y, w, h múltiplos de 8 sempre que der. Margem lateral de 56.
- **Destaque só o que importa.** No máximo 1 ou 2 caixas `destaque` por desenho.
- **Setas em ângulo reto**, nunca diagonais. Prefira `de`/`para` com âncoras a pontos soltos.
- **Linguagem simples**, em português do Brasil, sem jargão desnecessário.
- **Nunca exponha cliente nem segredo de negócio.** Anonimize nomes ("plataforma de planejamento de um cliente B2B"), não mostre regras, números ou módulos reais sem autorização.
- **Nunca invente** componentes, números ou integrações que não existam.

## Referência do JSON

```json
{
  "kicker": "// decisão 01 · tema",
  "titulo": "A mensagem em uma frase",
  "largura": 1280,
  "altura": 500,
  "nota_rodape": "frase curta opcional à esquerda da assinatura",
  "elementos": [ ... ]
}
```

| `tipo` | Campos | Para quê |
|---|---|---|
| `caixa` | `id`, `x`, `y`, `w`, `h`, `texto`, `sub`, `estilo`, `tamanho`, `raio` | blocos. Estilos: `normal`, `contorno`, `pill`, `destaque`, `grupo` (moldura com título no topo), `apagado` (legado), `tracejado` (desligado), `novo` |
| `chips` | `cx`, `y`, `itens` | fila de etiquetas centralizada. Item que começa com `+` sai tracejado |
| `seta` | `de`, `para`, `forma` (`vertical` ou `horizontal`), `meio`, `rotulo`, `estilo` (`fraca`) | liga caixas. `de`/`para` aceitam `"id.lado"` (`cima`, `baixo`, `esq`, `dir`, com deslocamento opcional `baixo:0.3`) ou `[x, y]` |
| `divisoria` | `x`, `y1`, `y2`, `rotulo` | linha tracejada vertical, ex.: isolamento |
| `texto` | `x`, `y`, `texto`, `estilo` (`rotulo`, `legenda`, `nota`, `titulo`), `alinha` | rótulos soltos |

`altura` é só a área do desenho; a faixa da assinatura (56 px) é somada no fim.

## Estilo e assinatura

- `config/estilo.json`: cores e fontes do tema escuro (padrão). `--tema claro` usa `config/estilo-claro.json` (fundo branco, azul #2563eb), bom para sites e documentos claros. `config/assinatura.json`: nome, usuário do GitHub (para o avatar) e link.
- Para usar os seus dados sem mexer no plugin, crie `~/.config/diagram-studio/assinatura.json` (e `estilo.json`, se quiser outra paleta). Esses arquivos têm prioridade.
- O avatar é baixado de `github.com/<usuario>.png` uma vez, fica em cache em `~/.cache/diagram-studio/` e entra embutido no SVG (o GitHub não carrega imagens externas dentro de SVG). Sem rede, aparecem as iniciais. Se `avatar_arquivo` apontar para uma imagem (relativa a `config/` ou caminho absoluto), ela tem prioridade sobre o GitHub. O padrão do plugin usa `config/avatar.jpg`.
- Sem assinatura: `{ "ativa": false }` no arquivo do usuário (vale sempre) ou `--sem-assinatura` (vale uma vez).
- O GitHub mostra SVG como imagem e **não carrega webfonts**: Montserrat e JetBrains Mono caem para a fonte do sistema. No PNG também, a menos que as fontes estejam instaladas.
