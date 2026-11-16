# /// script
# requires-python = ">=3.10"
# dependencies = ["resvg-py>=0.1"]
# ///
"""diagram-studio: gera diagramas técnicos em SVG e PNG a partir de um JSON simples.

Uso:
  uv run scripts/diagrama.py exemplos/personas.json --saida docs/img/personas
  -> docs/img/personas.svg e docs/img/personas.png

O JSON descreve só o que importa: título, caixas, chips, setas e divisórias.
O script cuida do resto: estilo, grade, setas em ângulo reto, texto que cabe
e a assinatura no canto (avatar do GitHub, nome e link).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
import xml.dom.minidom
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "diagram-studio"

# fator médio de largura por caractere (em relação ao tamanho da fonte)
F_SANS, F_SANS_BOLD, F_MONO = 0.56, 0.62, 0.62


# ---------------------------------------------------------------- config

def carregar_json(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def carregar_config(estilo_arq: str | None, assinatura_arq: str | None) -> tuple[dict, dict]:
    estilo = carregar_json(RAIZ / "config" / "estilo.json")
    assinatura = carregar_json(RAIZ / "config" / "assinatura.json")
    # o usuário pode sobrescrever com arquivos próprios (no projeto ou em ~/.config)
    local = Path.home() / ".config" / "diagram-studio"
    for base, nome, alvo in [(estilo_arq, "estilo.json", estilo), (assinatura_arq, "assinatura.json", assinatura)]:
        arq = Path(base) if base else local / nome
        if arq.exists():
            alvo.update(carregar_json(arq))
    return estilo, assinatura


def avatar_data_uri(assinatura: dict) -> str | None:
    """Baixa o avatar do GitHub uma vez, guarda em cache e devolve em base64.
    O GitHub bloqueia imagens externas dentro de SVG, por isso embutimos."""
    if assinatura.get("avatar_arquivo"):
        arq = Path(assinatura["avatar_arquivo"]).expanduser()
        if not arq.is_absolute():  # caminho relativo = dentro de config/
            arq = RAIZ / "config" / arq
        if arq.exists():
            mime = "image/jpeg" if arq.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            return f"data:{mime};base64," + base64.b64encode(arq.read_bytes()).decode()
        print(f"aviso: avatar_arquivo não encontrado ({arq}); tentando o GitHub", file=sys.stderr)
    user = assinatura.get("github")
    if not user:
        return None
    arq = CACHE / f"avatar-{user}.png"
    if not arq.exists():
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(f"https://github.com/{user}.png?size=120", timeout=10) as r:
                arq.write_bytes(r.read())
        except Exception as e:  # sem rede: cai para as iniciais
            print(f"aviso: não consegui baixar o avatar ({e}); usando as iniciais", file=sys.stderr)
            return None
    return "data:image/png;base64," + base64.b64encode(arq.read_bytes()).decode()


# ---------------------------------------------------------------- texto

def cabe(texto: str, tamanho: float, largura: float, fator: float = F_SANS) -> float:
    """Maior fonte (<= tamanho) em que o texto cabe na largura."""
    if not texto:
        return tamanho
    return max(10.0, min(tamanho, largura / (len(texto) * fator)))


def txt(x, y, s, tam, cor, fonte, peso=500, ancora="middle", espaco=0):
    ls = f' letter-spacing="{espaco}"' if espaco else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fonte}" font-size="{tam:.1f}" '
            f'font-weight="{peso}" fill="{cor}" text-anchor="{ancora}"{ls}>{escape(s)}</text>')


# ---------------------------------------------------------------- desenho

class Diagrama:
    def __init__(self, spec: dict, estilo: dict, assinatura: dict):
        self.s, self.e, self.a = spec, estilo, assinatura
        self.w = spec.get("largura", 1280)
        self.h_conteudo = spec.get("altura", 500)
        self.rodape = 56 if assinatura.get("ativa", True) else 0
        self.h = self.h_conteudo + self.rodape
        self.caixas: dict[str, tuple[float, float, float, float]] = {}
        self.partes: list[str] = []
        self.avisos: list[str] = []

    # cores e fontes
    def c(self, nome):
        return self.e["cores"][nome]

    @property
    def sans(self):
        return self.e["fontes"]["sans"]

    @property
    def mono(self):
        return self.e["fontes"]["mono"]

    def add(self, x):
        self.partes.append(x)

    # ---- elementos
    def caixa(self, el):
        x, y, w, h = el["x"], el["y"], el["w"], el["h"]
        est = el.get("estilo", "normal")
        rx = h / 2 if est == "pill" else el.get("raio", 10)
        fundo, borda, cor_t, cor_sub, tracejado = {
            "normal": (self.c("painel"), self.c("borda"), self.c("texto"), self.c("suave"), False),
            "contorno": (self.c("painel"), self.c("acento"), self.c("texto"), self.c("suave"), False),
            "pill": (self.c("painel"), self.c("acento"), self.c("texto"), self.c("suave"), False),
            "destaque": (self.c("acento"), self.c("acento"), self.c("fundo"), self.c("fundo"), False),
            "grupo": (self.c("grupo"), self.c("acento"), self.c("acento"), self.c("suave"), False),
            "apagado": (self.c("apagado"), self.c("apagado_borda"), self.c("fraco"), self.c("fraco"), False),
            "tracejado": ("none", self.c("apagado_borda"), self.c("fraco"), self.c("fraco"), True),
            "novo": ("none", self.c("acento"), self.c("acento"), self.c("suave"), True),
        }[est]
        d = ' stroke-dasharray="6 5"' if tracejado else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fundo}" '
                 f'stroke="{borda}" stroke-width="1.5"{d}/>')
        if el.get("id"):
            self.caixas[el["id"]] = (x, y, w, h)
        titulo, sub = el.get("texto", ""), el.get("sub", "")
        cx = x + w / 2
        pad = 24
        if est == "grupo":  # título pequeno no topo, conteúdo vai dentro
            tam = cabe(titulo, 12, w - pad, F_MONO)
            self.add(txt(cx, y + 22, titulo, tam, cor_t, self.mono, 700))
            return
        tam_t = cabe(titulo, el.get("tamanho", 17 if h >= 60 else 15), w - pad, F_SANS_BOLD)
        if tam_t < el.get("tamanho", 15) * 0.75:
            self.avisos.append(f'texto "{titulo}" ficou pequeno; aumente a caixa ou encurte')
        peso = 800 if est == "destaque" or h >= 60 else 600
        if sub:
            tam_s = cabe(sub, 13, w - pad, F_SANS)
            self.add(txt(cx, y + h / 2 - 2, titulo, tam_t, cor_t, self.sans, peso))
            self.add(txt(cx, y + h / 2 + tam_s + 4, sub, tam_s, cor_sub, self.sans, 600 if est == "destaque" else 500))
        else:
            self.add(txt(cx, y + h / 2 + tam_t * 0.35, titulo, tam_t, cor_t, self.sans, peso))

    def chips(self, el):
        """Fila de chips centralizada em cx. Chip que começa com + fica tracejado."""
        itens, cx, y = el["itens"], el["cx"], el["y"]
        tam, h, gap = 13, 30, 10
        larg = [len(i) * tam * F_SANS + 28 for i in itens]
        x = cx - (sum(larg) + gap * (len(itens) - 1)) / 2
        for i, w in zip(itens, larg):
            novo = i.startswith("+")
            d = ' stroke-dasharray="5 4"' if novo else ""
            fundo = "none" if novo else self.c("grupo")
            self.add(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h/2}" fill="{fundo}" '
                     f'stroke="{self.c("acento")}" stroke-width="1.5"{d}/>')
            self.add(txt(x + w / 2, y + 20, i, tam, self.c("acento") if novo else self.c("suave"), self.sans))
            x += w + gap

    def ancora(self, ref):
        """'id.baixo' -> ponto. Lados: cima, baixo, esq, dir (padrão: baixo / cima)."""
        if isinstance(ref, list):
            return tuple(ref)
        nome, _, lado = ref.partition(".")
        x, y, w, h = self.caixas[nome]
        frac = 0.5
        if ":" in lado:  # ex.: baixo:0.3 desloca a ponta ao longo do lado
            lado, f = lado.split(":")
            frac = float(f)
        return {
            "cima": (x + w * frac, y), "baixo": (x + w * frac, y + h),
            "esq": (x, y + h * frac), "dir": (x + w, y + h * frac),
        }[lado or "baixo"]

    def seta(self, el):
        """Seta em ângulo reto. 'de'/'para' aceitam 'id.lado' ou [x, y]."""
        if "pontos" in el:
            pts = [tuple(p) for p in el["pontos"]]
        else:
            (x1, y1), (x2, y2) = self.ancora(el["de"]), self.ancora(el["para"])
            if abs(x1 - x2) < 1 or abs(y1 - y2) < 1:
                pts = [(x1, y1), (x2, y2)]
            elif el.get("forma", "vertical") == "vertical":  # desce, anda, desce
                ym = el.get("meio", (y1 + y2) / 2)
                pts = [(x1, y1), (x1, ym), (x2, ym), (x2, y2)]
            else:  # anda, desce, anda
                xm = el.get("meio", (x1 + x2) / 2)
                pts = [(x1, y1), (xm, y1), (xm, y2), (x2, y2)]
        # recua a ponta 2px para a cabeça não invadir a borda
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        dx, dy = (xb > xa) - (xb < xa), (yb > ya) - (yb < ya)
        pts[-1] = (xb - dx * 2, yb - dy * 2)
        d = "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
        cor = self.c("fraco") if el.get("estilo") == "fraca" else self.c("acento")
        das = ' stroke-dasharray="6 5"' if el.get("estilo") == "fraca" else ""
        mk = "url(#ar-fraca)" if el.get("estilo") == "fraca" else "url(#ar)"
        self.add(f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2"{das} marker-end="{mk}"/>')
        if el.get("rotulo"):
            mx = (pts[len(pts) // 2 - 1][0] + pts[len(pts) // 2][0]) / 2
            my = (pts[len(pts) // 2 - 1][1] + pts[len(pts) // 2][1]) / 2
            self.add(txt(mx + 8, my - 6, el["rotulo"], 12, self.c("suave"), self.mono, 500, "start"))

    def divisoria(self, el):
        x, y1, y2 = el["x"], el["y1"], el["y2"]
        self.add(f'<path d="M{x} {y1}V{y2}" stroke="{self.c("fraco")}" stroke-width="2" stroke-dasharray="8 6"/>')
        if el.get("rotulo"):
            r = el["rotulo"]
            w = len(r) * 13 * F_MONO + 16
            ym = (y1 + y2) / 2
            self.add(f'<rect x="{x - w/2:.1f}" y="{ym - 16:.1f}" width="{w:.1f}" height="28" fill="{self.c("fundo")}"/>')
            self.add(txt(x, ym + 3, r, 13, self.c("fraco"), self.mono, 700))

    def texto(self, el):
        estilos = {
            "rotulo": (13, self.c("acento"), self.mono, 700),
            "legenda": (15, self.c("suave"), self.sans, 500),
            "nota": (13, self.c("fraco"), self.mono, 500),
            "titulo": (18, self.c("texto"), self.sans, 800),
        }
        tam, cor, fonte, peso = estilos[el.get("estilo", "legenda")]
        self.add(txt(el["x"], el["y"], el["texto"], el.get("tamanho", tam), cor, fonte, peso, el.get("alinha", "middle")))

    # ---- moldura
    def cabecalho(self):
        bg, grade = self.c("fundo"), self.c("grade")
        self.add(f'''<defs>
<pattern id="g" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{grade}"/></pattern>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="{self.c("acento")}"/></marker>
<marker id="ar-fraca" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="{self.c("fraco")}"/></marker>
<clipPath id="av"><circle cx="0" cy="0" r="16"/></clipPath>
</defs>
<rect width="{self.w}" height="{self.h}" rx="16" fill="{bg}"/>
<rect width="{self.w}" height="{self.h}" rx="16" fill="url(#g)"/>''')
        if self.s.get("kicker"):
            self.add(txt(56, 52, self.s["kicker"].upper(), 14, self.c("acento"), self.mono, 400, "start", 2))
        if self.s.get("titulo"):
            tam = cabe(self.s["titulo"], 28, self.w - 112, F_SANS_BOLD)
            self.add(txt(56, 88, self.s["titulo"], tam, self.c("texto"), self.sans, 800, "start"))

    def assinatura(self):
        if not self.rodape:
            return
        a = self.a
        y0 = self.h_conteudo
        self.add(f'<path d="M56 {y0}H{self.w - 56}" stroke="{self.c("borda")}" stroke-width="1"/>')
        nome, link = a.get("nome", ""), a.get("link", "")
        rotulo = link.replace("https://", "").replace("www.", "")
        larg_texto = max(len(nome) * 14 * F_SANS_BOLD, len(rotulo) * 12 * F_MONO)
        cx = self.w - 56 - larg_texto - 28
        cy = y0 + 28
        grupo = []
        uri = avatar_data_uri(a)
        if uri:
            grupo.append(f'<g transform="translate({cx:.1f} {cy})"><image href="{uri}" x="-16" y="-16" width="32" height="32" clip-path="url(#av)"/></g>')
        else:
            ini = "".join(p[0] for p in nome.split()[:2]).upper()
            grupo.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="16" fill="{self.c("acento")}"/>')
            grupo.append(txt(cx, cy + 5, ini, 13, self.c("fundo"), self.sans, 800))
        grupo.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="16" fill="none" stroke="{self.c("acento")}" stroke-width="1.5"/>')
        grupo.append(txt(cx + 26, cy - 2, nome, 14, self.c("texto"), self.sans, 700, "start"))
        grupo.append(txt(cx + 26, cy + 14, rotulo, 12, self.c("suave"), self.mono, 400, "start"))
        corpo = "".join(grupo)
        self.add(f'<a href="{escape(link)}">{corpo}</a>' if link else corpo)
        if self.s.get("nota_rodape"):
            self.add(txt(56, cy + 5, self.s["nota_rodape"], 13, self.c("fraco"), self.sans, 500, "start"))

    def render(self) -> str:
        self.cabecalho()
        for el in self.s.get("elementos", []):
            getattr(self, el["tipo"])(el)
        self.assinatura()
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}">\n' + "\n".join(self.partes) + "\n</svg>\n")
        xml.dom.minidom.parseString(svg.encode())  # garante XML válido
        return svg


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="arquivo JSON do diagrama")
    ap.add_argument("--saida", help="caminho sem extensão (padrão: ao lado do JSON)")
    ap.add_argument("--estilo", help="estilo.json próprio")
    ap.add_argument("--assinatura", help="assinatura.json própria")
    ap.add_argument("--sem-assinatura", action="store_true")
    ap.add_argument("--sem-png", action="store_true")
    args = ap.parse_args()

    spec = carregar_json(Path(args.spec))
    estilo, assinatura = carregar_config(args.estilo, args.assinatura)
    if args.sem_assinatura:
        assinatura["ativa"] = False

    d = Diagrama(spec, estilo, assinatura)
    svg = d.render()
    base = Path(args.saida) if args.saida else Path(args.spec).with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".svg").write_text(svg, encoding="utf-8")
    print(f"ok: {base.with_suffix('.svg')}")

    if not args.sem_png:
        import resvg_py
        png = resvg_py.svg_to_bytes(svg_string=svg, width=d.w * 2)
        base.with_suffix(".png").write_bytes(bytes(png))
        print(f"ok: {base.with_suffix('.png')}")
    for a in d.avisos:
        print("aviso:", a, file=sys.stderr)


if __name__ == "__main__":
    main()
