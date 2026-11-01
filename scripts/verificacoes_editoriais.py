#!/usr/bin/env python3
"""
verificacoes_editoriais.py — Gera TODOS os numeros citados no informativo.

Regra do projeto: nenhum numero publicado sem comando que o produza.
Este script e a prova. Rode-o para conferir cada afirmacao.

    python3 scripts/verificacoes_editoriais.py           # tudo
    python3 scripts/verificacoes_editoriais.py --check N # so um bloco
    python3 scripts/verificacoes_editoriais.py --json    # saida maquina

Le APENAS dados/Estacoes_Radioamador.csv (fonte: Anatel, dados abertos).
Nao usa o SQLite, para que o resultado seja independente do banco local.
"""

import csv
import io
import json
import os
import sys
import collections
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(BASE, "dados", "Estacoes_Radioamador.csv")

_cache = {}


def linhas():
    if "rows" not in _cache:
        with open(CSV, encoding="utf-8-sig", errors="replace") as f:
            _cache["rows"] = list(csv.DictReader(f, delimiter=";"))
    return _cache["rows"]


def c(r, k):
    return (r.get(k) or "").strip()


def pct(a, b):
    return f"{100*a/b:.1f}%" if b else "0%"


def cabecalho(n, titulo):
    print()
    print("=" * 72)
    print(f"BLOCO {n} — {titulo}")
    print("=" * 72)


# ---------------------------------------------------------------------------
def b1_universo():
    cabecalho(1, "UNIVERSO: estacoes x pessoas x indicativos")
    R = linhas()
    total = len(R)
    cpfs = {c(r, "CNPJ ou CPF") for r in R if c(r, "CNPJ ou CPF")}
    inds = {c(r, "Indicativo").upper() for r in R if c(r, "Indicativo")}
    cnpj_linhas = sum(1 for r in R if c(r, "Tipo de Identificação") == "CNPJ")
    cnpj_dist = {c(r, "CNPJ ou CPF") for r in R
                 if c(r, "Tipo de Identificação") == "CNPJ"}

    # decomposicao do misterio dos indicativos
    por_doc = collections.defaultdict(set)
    for r in R:
        d, i = c(r, "CNPJ ou CPF"), c(r, "Indicativo").upper()
        if d and i:
            por_doc[d].add(i)
    multi = sum(1 for v in por_doc.values() if len(v) > 1)
    extra = sum(len(v) - 1 for v in por_doc.values())
    por_ind = collections.defaultdict(set)
    for r in R:
        d, i = c(r, "CNPJ ou CPF"), c(r, "Indicativo").upper()
        if d and i:
            por_ind[i].add(d)
    compartilhados = sum(1 for v in por_ind.values() if len(v) > 1)
    dup = sum(len(v) - 1 for v in por_ind.values())

    print(f"linhas no CSV ................ {total:,}")
    print(f"documentos distintos ........ {len(cpfs):,}")
    print(f"indicativos distintos ....... {len(inds):,}")
    print(f"linhas CNPJ ................. {cnpj_linhas:,}")
    print(f"CNPJs distintos ............. {len(cnpj_dist):,}")
    print()
    print("CONTA DO MISTERIO 46.670 x 35.498:")
    print(f"  documentos distintos ................... {len(cpfs):,}")
    print(f"  + documentos com mais de 1 indicativo ... {extra:,} "
          f"(de {multi:,} documentos multi-indicativo)")
    print(f"  - indicativos compartilhados por 2+ docs  {dup:,} "
          f"(de {compartilhados:,} indicativos)")
    print(f"  = {len(cpfs) + extra - dup:,}   "
          f"{'CONFERE' if len(cpfs)+extra-dup == len(inds) else 'NAO CONFERE'}"
          f" com {len(inds):,}")
    return {"total": total, "docs": len(cpfs), "indicativos": len(inds)}


def b2_tipos_classes():
    cabecalho(2, "TIPOS DE ESTACAO E CLASSES")
    R = linhas()
    n = len(R)
    print("Tipo de estacao:")
    for k, v in collections.Counter(c(r, "Tipo de Estação") for r in R).most_common():
        print(f"  {k or '(vazio)':14} {v:7,}  {pct(v, n)}")
    print("\nClasse (COER):")
    for k, v in collections.Counter(c(r, "COER") for r in R).most_common():
        print(f"  {k or '(vazio)':14} {v:7,}  {pct(v, n)}")
    print("\nTipo x Classe (matriz):")
    tipos = ["Fixa", "Móvel", "Repetidora", "Terrena"]
    classes = ["Classe A", "Classe B", "Classe C", "N/A"]
    print(f"  {'':12}" + "".join(f"{x:>11}" for x in classes))
    for t in tipos:
        sub = [r for r in R if c(r, "Tipo de Estação") == t]
        linha = "".join(f"{sum(1 for r in sub if c(r,'COER')==cl):>11,}" for cl in classes)
        print(f"  {t:12}{linha}")


def b3_repetidoras():
    cabecalho(3, "REPETIDORAS")
    R = linhas()
    rep = [r for r in R if c(r, "Tipo de Estação") == "Repetidora"]
    print(f"total de repetidoras ........ {len(rep):,}")
    print("\npor classe:")
    for k, v in collections.Counter(c(r, "COER") for r in rep).most_common():
        print(f"  {k or '(vazio)':14} {v:6,}")
    print("\nrepetidoras com CNPJ (pessoa juridica): "
          f"{sum(1 for r in rep if c(r,'Tipo de Identificação')=='CNPJ'):,}")
    print("repetidoras com COER N/A: "
          f"{sum(1 for r in rep if c(r,'COER')=='N/A'):,}")

    # as 35 de classe B: quando foram licenciadas?
    b = [r for r in rep if c(r, "COER") == "Classe B"]
    anos = collections.Counter(
        c(r, "Data do Primeiro Licenciamento").split("/")[-1] for r in b
        if "/" in c(r, "Data do Primeiro Licenciamento"))
    print(f"\nREPETIDORAS CLASSE B: {len(b)}")
    print("primeiro licenciamento por ano:")
    for a, v in sorted(anos.items()):
        print(f"  {a}: {v}")
    print("\nexemplos:")
    for r in b[:6]:
        print(f"  {c(r,'Indicativo'):8} {c(r,'Nome da Entidade')[:34]:34} "
              f"{c(r,'Município da Estação')}/{c(r,'UF da Entidade')} "
              f"1o={c(r,'Data do Primeiro Licenciamento')}")

    print(f"\nrepetidoras por UF (total {len(rep):,}):")
    for k, v in collections.Counter(c(r, "UF da Entidade") for r in rep).most_common(10):
        print(f"  {k}: {v}")
    ufs_todas = {c(r, "UF da Entidade") for r in R if c(r, "UF da Entidade")}
    ufs_rep = {c(r, "UF da Entidade") for r in rep}
    print(f"\nUFs sem nenhuma repetidora: {sorted(ufs_todas - ufs_rep)}")
    print(f"razao estacoes/repetidora: {len(R)/len(rep):.1f} estacoes por repetidora")

    # repetidoras com status N/I (potencial inatividade — art. 10-B §4)
    print(f"\nrepetidoras com status N/I: "
          f"{sum(1 for r in rep if c(r,'Status da Validade')=='N/I'):,} "
          f"({pct(sum(1 for r in rep if c(r,'Status da Validade')=='N/I'), len(rep))})")
    print(f"repetidoras com status Vencida: "
          f"{sum(1 for r in rep if c(r,'Status da Validade')=='Vencida'):,}")
    return {"repetidoras": len(rep), "classe_b": len(b), "anos_b": dict(anos)}


def b4_geografia():
    cabecalho(4, "GEOGRAFIA: UF, MUNICIPIOS E PREFIXOS")
    R = linhas()
    n = len(R)
    uf = collections.Counter(c(r, "UF da Entidade") for r in R)
    print("estacoes por UF (todas):")
    acum = 0
    for i, (k, v) in enumerate(uf.most_common(), 1):
        acum += v
        print(f"  {i:2}. {k} {v:6,}  {pct(v,n):>6}  acumulado {pct(acum,n):>6}")
    top4 = sum(v for _, v in uf.most_common(4))
    print(f"\n4 primeiras UFs somam {top4:,} = {pct(top4,n)}")

    print("\nPESSOAS por UF (documentos distintos):")
    docs_uf = collections.defaultdict(set)
    for r in R:
        d = c(r, "CNPJ ou CPF")
        if d:
            docs_uf[c(r, "UF da Entidade")].add(d)
    for k, v in sorted(docs_uf.items(), key=lambda x: -len(x[1]))[:8]:
        print(f"  {k}: {len(v):,} pessoas")

    # municipios
    mun = collections.Counter(
        (c(r, "Município da Estação"), c(r, "UF da Entidade")) for r in R
        if c(r, "Município da Estação") not in ("", "N/A", "N/I"))
    print(f"\nmunicipios distintos com estacao fixa/repetidora: {len(mun):,}")
    print("top 10:")
    for (m, u), v in mun.most_common(10):
        print(f"  {m}/{u}: {v}")
    print("(municipios do Brasil segundo IBGE: 5.570 -> "
          f"{pct(len(mun), 5570)} de cobertura)")

    # prefixos
    print("\nconcentracao por regiao (digito do indicativo):")
    reg = collections.Counter()
    for r in R:
        i = c(r, "Indicativo").upper()
        if len(i) >= 3 and i[2].isdigit():
            reg[i[2]] += 1
    for k, v in sorted(reg.items()):
        print(f"  regiao {k}: {v:6,}  {pct(v,n)}")


def b5_serie():
    cabecalho(5, "SERIE HISTORICA (primeiro licenciamento)")
    R = linhas()
    anos = collections.Counter()
    for r in R:
        d = c(r, "Data do Primeiro Licenciamento")
        if "/" in d:
            a = d.split("/")[-1]
            if a.isdigit():
                anos[a] += 1
    print("anos com mais licenciamentos:")
    for a, v in sorted(anos.items(), key=lambda x: -x[1])[:12]:
        print(f"  {a}: {v:6,}")
    print("\nultimos 15 anos em ordem:")
    for a in sorted(anos)[-15:]:
        print(f"  {a}: {anos[a]:6,}")
    print("\nfaixas:")
    def s(lo, hi):
        return sum(v for k, v in anos.items() if lo <= int(k) <= hi)
    print(f"  antes de 2000: {s(1900,1999):,}")
    print(f"  2000-2010 ...: {s(2000,2010):,}")
    print(f"  2011-2020 ...: {s(2011,2020):,}")
    print(f"  2021-2026 ...: {s(2021,2026):,}")
    print(f"  pico: {max(anos.items(), key=lambda x: x[1])}")
    janela = [(int(a), v) for a, v in anos.items() if 2013 <= int(a) <= 2020]
    piso = min(janela, key=lambda x: x[1])
    print(f"  piso 2013-2020: {piso[0]} com {piso[1]:,}")
    pico = max(anos.items(), key=lambda x: x[1])
    print(f"  queda pico->piso: {100*(pico[1]-piso[1])/pico[1]:.1f}%")
    a25 = anos.get("2025", 0)
    if a25 and piso[1]:
        print(f"  recuperacao piso->2025: {100*(a25-piso[1])/piso[1]:.0f}%")
    print("\nATENCAO 2026 esta incompleto (extracao em 31/10/2026).")
    return {"anos": dict(anos)}


def b6_qualidade():
    cabecalho(6, "QUALIDADE DA BASE (o que NAO sabemos)")
    R = linhas()
    n = len(R)
    print(f"{'campo':34} {'vazio/NI':>10} {'%':>7}")
    for k in R[0].keys():
        v = sum(1 for r in R if c(r, k) in ("", "N/I", "N/A", "-"))
        print(f"{k:34} {v:10,} {pct(v,n):>7}")
    print("\nstatus de validade:")
    for k, v in collections.Counter(c(r, "Status da Validade") for r in R).most_common():
        print(f"  {k or '(vazio)':14} {v:7,}  {pct(v,n)}")
    venc = [r for r in R if c(r, "Status da Validade") == "Vencida"]
    print(f"\nvencidas: {len(venc):,}")
    for k, v in collections.Counter(c(r, "UF da Entidade") for r in venc).most_common(6):
        print(f"  {k}: {v}")


def b7_paraiba():
    cabecalho(7, "CASOS ESPECIAIS: Paraiba, Acre, coletivas")
    R = linhas()
    uf = collections.Counter(c(r, "UF da Entidade") for r in R)
    docs_uf = collections.defaultdict(set)
    for r in R:
        if c(r, "CNPJ ou CPF"):
            docs_uf[c(r, "UF da Entidade")].add(c(r, "CNPJ ou CPF"))
    print("PB x UFs comparaveis:")
    for u in ["PB", "BA", "PE", "RN", "CE", "DF"]:
        print(f"  {u}: {uf[u]:6,} estacoes, {len(docs_uf[u]):5,} pessoas, "
              f"{uf[u]/max(len(docs_uf[u]),1):.2f} estacoes/pessoa")
    ace = [r for r in R if c(r, "UF da Entidade") == "AC"]
    print(f"\nACRE: {len(ace)} estacoes, {len(docs_uf['AC'])} pessoas")
    print("  por tipo:", dict(collections.Counter(c(r, "Tipo de Estação") for r in ace)))
    print("  municipios:", len({c(r,'Município da Estação') for r in ace
                               if c(r,'Município da Estação') not in ('','N/A','N/I')}))
    cnpj = [r for r in R if c(r, "Tipo de Identificação") == "CNPJ"]
    print(f"\nentidades coletivas: {len(cnpj):,} linhas, "
          f"{len({c(r,'CNPJ ou CPF') for r in cnpj}):,} CNPJs")
    top = collections.Counter(c(r, "Nome da Entidade") for r in cnpj)
    print("  com mais estacoes:")
    for k, v in top.most_common(5):
        print(f"    {k[:50]}: {v}")


BLOCOS = {1: b1_universo, 2: b2_tipos_classes, 3: b3_repetidoras,
          4: b4_geografia, 5: b5_serie, 6: b6_qualidade, 7: b7_paraiba}


def main():
    args = sys.argv[1:]
    print(f"Verificacoes editoriais — fonte: {os.path.basename(CSV)}")
    print(f"Executado em {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Total de linhas: {len(linhas()):,}")
    if "--check" in args:
        try:
            n = int(args[args.index("--check") + 1])
        except (IndexError, ValueError):
            print("Uso: --check N   (N de 1 a 7). Blocos disponiveis:")
            for k, f in BLOCOS.items():
                print(f"  {k}: {f.__name__}")
            return 2
        if n not in BLOCOS:
            print(f"Bloco {n} nao existe. Disponiveis: {sorted(BLOCOS)}")
            return 2
        BLOCOS[n]()
        return 0
    if "--json" in args:
        dados = {n: f() for n, f in BLOCOS.items()}
        print(json.dumps(dados, ensure_ascii=False, indent=1))
        return 0
    for n, f in BLOCOS.items():
        f()
    print("\n" + "=" * 72)
    print("FIM. Todo numero deste arquivo e reproduzivel com este comando.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
