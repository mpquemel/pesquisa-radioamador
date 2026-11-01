#!/usr/bin/env python3
"""
Coletor de legislacao do radioamadorismo brasileiro.

Baixa os atos normativos que regem o Servico de Radioamador e o Servico de
Radio do Cidadao, converte para texto limpo em Markdown e guarda com metadados
de fonte e data de captura.

Fontes (em ordem de preferencia):
  1. informacoes.anatel.gov.br / legislacao.anatel.gov.br  -> oficial
  2. www.legisweb.com.br                                    -> espelho (fallback)
  3. sistemas.anatel.gov.br/anexar-api/...                  -> PDFs de cartilhas

Uso:
    python3 scripts/coletar_legislacao.py            # baixa o que falta
    python3 scripts/coletar_legislacao.py --force    # rebaixa tudo
    python3 scripts/coletar_legislacao.py --list     # mostra o catalogo

Saida:
    legislacao/<slug>.md       texto limpo
    legislacao/<slug>.html     original
    legislacao/INDICE.md       catalogo com status de cada ato
"""

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "legislacao")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# ---------------------------------------------------------------------------
# Catalogo dos atos normativos
# ---------------------------------------------------------------------------
ATOS = [
    {
        "slug": "res-777-2025",
        "titulo": "Resolucao Anatel n. 777, de 28 de abril de 2025",
        "assunto": "Altera o Regulamento Geral de Licenciamento. Inclui o art. 10-B "
                   "(tipos de estacao de radioamador) e da nova redacao ao art. 16 "
                   "(titular de repetidora).",
        "urgencia": "alta",
        "urls": [
            "https://informacoes.anatel.gov.br/legislacao/component/content/article/170-resolucoes/2025/2022-resolucao-777",
            "https://informacoes.anatel.gov.br/legislacao/resolucoes/2025/2022-resolucao-777",
        ],
    },
    {
        "slug": "res-719-2020",
        "titulo": "Resolucao Anatel n. 719, de 10 de fevereiro de 2020",
        "assunto": "Regulamento Geral de Licenciamento. Norma-mae do licenciamento "
                   "de estacoes, inclusive as de radioamador.",
        "urgencia": "alta",
        "urls": [
            "https://informacoes.anatel.gov.br/legislacao/resolucoes/2020/1381-resolucao-719",
            "https://www.legisweb.com.br/legislacao/?id=389749",
        ],
    },
    {
        "slug": "res-449-2006",
        "titulo": "Resolucao Anatel n. 449, de 20 de setembro de 2006",
        "assunto": "Regulamento do Servico de Radioamador. Art. 44 tratava do titular "
                   "de repetidora (exigencia de Classe A), revogado pela Res. 777/2025.",
        "urgencia": "alta",
        "urls": [
            "https://informacoes.anatel.gov.br/legislacao/resolucoes/2006/321-resolucao-449",
            "https://www.legisweb.com.br/legislacao/?id=100077",
        ],
    },
    {
        "slug": "norma-31-94",
        "titulo": "Norma n. 31/94 - Norma de Execucao do Servico de Radioamador",
        "assunto": "Norma antiga de execucao do servico. Ainda citada em procedimentos "
                   "de indicativo e estacao.",
        "urgencia": "media",
        "urls": [
            "https://www.anatel.gov.br/Portal/verificaDocumentos/documento.asp?numeroPublicacao=10244",
        ],
    },
    {
        "slug": "lei-9472-1997",
        "titulo": "Lei n. 9.472, de 16 de julho de 1997 - Lei Geral de Telecomunicacoes",
        "assunto": "Base legal de tudo: outorga, licenciamento, competencia da Anatel.",
        "urgencia": "media",
        "urls": [
            "https://www.planalto.gov.br/ccivil_03/leis/l9472.htm",
        ],
    },
    {
        "slug": "res-710-2019",
        "titulo": "Resolucao Anatel n. 710, de 24 de outubro de 2019",
        "assunto": "ATENCAO: NAO e norma de radioamador. Regulamento do SLP em 2,3 GHz. "
                   "Incluida no catalogo apenas para registrar a confusao e evita-la.",
        "urgencia": "baixa",
        "urls": [
            "https://informacoes.anatel.gov.br/legislacao/resolucoes/2019/1358-resolucao-710",
        ],
    },
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def agora():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def baixar(url, timeout=40):
    """Devolve (bytes, url_final, status). status 0 = falha de rede."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.geturl(), r.status
    except urllib.error.HTTPError as e:
        return b"", url, e.code
    except Exception as e:  # noqa: BLE001
        return b"", url, 0


def e_manutencao(url_final, corpo):
    """Detecta a pagina de manutencao da Anatel, que responde 200 enganoso."""
    if "aviso/manutencao" in (url_final or ""):
        return True
    amostra = corpo[:4000].decode("utf-8", "replace").lower()
    return "manuten" in amostra and "previs" in amostra


def html_para_texto(bruto):
    t = bruto.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<(br|/p|/div|/tr|/h[1-6])\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    linhas = [ln.strip() for ln in t.split("\n")]
    return "\n".join(linhas).strip()


def recortar_corpo(texto):
    """Remove cabecalho de navegacao, mantendo do titulo do ato em diante."""
    marcas = [
        "Aprova o Regulamento",
        "Regulamento Geral",
        "O Conselho Diretor",
        "RESOLVE",
        "Art. 1",
        "LEI N",
        "Norma de Execucao",
    ]
    pos = -1
    for m in marcas:
        p = texto.find(m)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos > 200:
        inicio = max(0, texto.rfind("\n", 0, pos - 200))
        return texto[inicio:].strip()
    return texto


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------
def coletar(ato, force=False):
    destino_md = os.path.join(OUT, ato["slug"] + ".md")
    destino_html = os.path.join(OUT, ato["slug"] + ".html")
    if os.path.exists(destino_md) and not force:
        return {"slug": ato["slug"], "status": "ja_existe",
                "fonte": "", "bytes": os.path.getsize(destino_md)}

    for url in ato["urls"]:
        corpo, final, status = baixar(url)
        if status != 200 or not corpo:
            print(f"  [{status}] {url}")
            continue
        if e_manutencao(final, corpo):
            print(f"  [MANUTENCAO] {url}")
            continue
        texto = html_para_texto(corpo)
        if len(texto) < 1500:
            print(f"  [CURTO {len(texto)}] {url}")
            continue

        texto = recortar_corpo(texto)
        cabecalho = (
            f"# {ato['titulo']}\n\n"
            f"**Assunto:** {ato['assunto']}\n"
            f"**Fonte:** {final}\n"
            f"**Capturado em:** {agora()}\n"
            f"**Aviso:** texto extraido automaticamente de pagina HTML. "
            f"Confira no original antes de citar em peca ou publicacao.\n\n---\n\n"
        )
        with open(destino_md, "w", encoding="utf-8") as f:
            f.write(cabecalho + texto + "\n")
        with open(destino_html, "wb") as f:
            f.write(corpo)
        print(f"  [OK {len(texto)} chars] {final}")
        return {"slug": ato["slug"], "status": "baixado", "fonte": final,
                "bytes": len(texto)}
    return {"slug": ato["slug"], "status": "falhou", "fonte": "", "bytes": 0}


def escrever_indice(resultados):
    mapa = {r["slug"]: r for r in resultados}
    linhas = [
        "# INDICE — Legislacao do Radioamadorismo",
        "",
        f"Atualizado em: {agora()}",
        "",
        "Coletado por `scripts/coletar_legislacao.py`. Texto extraido de HTML; "
        "**confirmar no original antes de citar**.",
        "",
        "| Ato | Urgencia | Status | Fonte |",
        "|---|---|---|---|",
    ]
    for ato in ATOS:
        r = mapa.get(ato["slug"], {})
        status = r.get("status", "pendente")
        fonte = r.get("fonte") or "—"
        if fonte.startswith("http"):
            fonte = f"[link]({fonte})"
        linhas.append(
            f"| {ato['titulo']} | {ato['urgencia']} | {status} | {fonte} |"
        )
    linhas += ["", "## Notas de assunto", ""]
    for ato in ATOS:
        linhas.append(f"- **{ato['slug']}** — {ato['assunto']}")
    with open(os.path.join(OUT, "INDICE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    force = "--force" in sys.argv
    if "--list" in sys.argv:
        for ato in ATOS:
            print(f"{ato['slug']:20} {ato['urgencia']:6} {ato['titulo']}")
        return

    print(f"Coletor de legislacao — saida em {OUT}")
    resultados = []
    for ato in ATOS:
        print(f"\n> {ato['slug']}")
        resultados.append(coletar(ato, force=force))
        time.sleep(1)
    escrever_indice(resultados)

    ok = sum(1 for r in resultados if r["status"] in ("baixado", "ja_existe"))
    print(f"\nResumo: {ok}/{len(ATOS)} disponiveis. Indice: legislacao/INDICE.md")


if __name__ == "__main__":
    main()
