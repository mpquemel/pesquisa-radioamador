#!/usr/bin/env python3
"""exp_04 - padroes nao explorados: prefixos, regiao, sazonalidade, outliers, coletivas."""
import csv, collections, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "dados" / "Estacoes_Radioamador.csv"

rows = []
with open(CSV, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        rows.append(r)

def cp(r): return (r["CNPJ ou CPF"] or "").strip()
def ind(r): return (r["Indicativo"] or "").strip()
def est(r): return (r["Número da Estação"] or "").strip()
def tdoc(r): return (r["Tipo de Identificação"] or "").strip()

# --- prefixo do indicativo (PY, PP, PT, PU, PV, PS, PR, etc) ---
pref = collections.Counter()
for r in rows:
    i = ind(r)
    m = re.match(r'^([A-Z]{2,3})', i)
    if m: pref[m.group(1)] += 1
print("=== Prefixo do indicativo (contagem de LINHAS) ===")
for p, n in pref.most_common():
    print(f"  {p}: {n}")

# prefixo por indicativo DISTINTO
pref_dist = collections.Counter()
for i in set(ind(r) for r in rows):
    m = re.match(r'^([A-Z]{2,3})', i)
    if m: pref_dist[m.group(1)] += 1
print("\n=== Prefixo por indicativo DISTINTO ===")
for p, n in pref_dist.most_common():
    print(f"  {p}: {n}")

# --- digito de regiao (PY1, PY2, ... PY0) ---
reg = collections.Counter()
for r in rows:
    i = ind(r)
    m = re.match(r'^[A-Z]{2}(\d)', i)
    if m: reg[m.group(1)] += 1
print("\n=== Digito de regiao (linhas) ===")
for d in "0123456789":
    print(f"  regiao {d}: {reg.get(d, 0)}")

# --- sazonalidade por mes de primeiro licenciamento ---
meses = collections.Counter()
for r in rows:
    d = (r["Data do Primeiro Licenciamento"] or "").strip()
    m = re.match(r'^(\d{2})/', d)
    if m: meses[int(m.group(1))] += 1
print("\n=== Primeiro licenciamento por mes ===")
for mm in range(1, 13):
    print(f"  mes {mm:02d}: {meses.get(mm, 0)}")

# --- outlier: CPF com 33 indicativos / 34 estacoes ---
cpf_est = collections.defaultdict(list)
for r in rows:
    c = cp(r)
    if c: cpf_est[c].append(r)
print("\n=== Top CPFs por total de estacoes (top 10) ===")
for c in sorted(cpf_est, key=lambda x: -len(cpf_est[x]))[:10]:
    rs = cpf_est[c]
    tipos = collections.Counter(r["Tipo de Estação"] for r in rs)
    inds = set(ind(r) for r in rs)
    print(f"  {c} ({rs[0]['Nome da Entidade']}): {len(rs)} estacoes, {len(inds)} indicativos, tipos={dict(tipos)}")

# --- entidades coletivas (CNPJ) com mais estacoes ---
cnpj_est = collections.defaultdict(list)
for r in rows:
    if tdoc(r) == "CNPJ":
        cnpj_est[cp(r)].append(r)
print("\n=== Top entidades coletivas (CNPJ) por estacoes ===")
for c in sorted(cnpj_est, key=lambda x: -len(cnpj_est[x]))[:10]:
    rs = cnpj_est[c]
    inds = set(ind(r) for r in rs)
    print(f"  {c} ({rs[0]['Nome da Entidade']}): {len(rs)} estacoes, {len(inds)} indicativos")
