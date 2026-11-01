#!/usr/bin/env python3
"""exp_05 - prefixo PU vs classe, regiao 0, municipios densos, UF razao, validade vencida."""
import csv, collections, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "dados" / "Estacoes_Radioamador.csv"

rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig"), delimiter=";"))
def ind(r): return (r["Indicativo"] or "").strip()
def cp(r): return (r["CNPJ ou CPF"] or "").strip()

# PU vs classe (PU e o prefixo moderno da Classe C)
print("=== Prefixo (2 letras) vs Classe COER ===")
pclass = collections.defaultdict(collections.Counter)
for r in rows:
    m = re.match(r'^([A-Z]{2})', ind(r))
    if m: pclass[m.group(1)][r["COER"]] += 1
for p in ["PU","PY","PP","PT","PR","PS","PV","PW","PQ"]:
    print(f"  {p}: {dict(pclass[p])}")

# regiao 0 - onde esta?
print("\n=== Indicativos com digito 0 ===")
reg0 = [r for r in rows if re.match(r'^[A-Z]{2}0', ind(r))]
print("linhas regiao 0:", len(reg0))
for r in reg0[:10]:
    print(f"  {ind(r)} | {r['Nome da Entidade']} | {r['UF da Entidade']} | {r['COER']}")

# distribuicao regiao completa
reg = collections.Counter()
for r in rows:
    m = re.match(r'^[A-Z]{2}(\d)', ind(r))
    if m: reg[m.group(1)] += 1
print("\n=== Regiao completa ===")
for d in "0123456789":
    print(f"  {d}: {reg.get(d,0)}")

# --- municipios com muitas estacoes fixas/repetidoras (ja no retrato, mas aprofundar razao) ---
# razao estacoes por pessoa por UF
uf_pessoas = collections.Counter()
uf_est = collections.Counter()
for r in rows:
    uf = r["UF da Entidade"].strip()
    uf_est[uf] += 1
    uf_pessoas[(uf, cp(r))] = 1
print("\n=== UF: estacoes e pessoas distintas ===")
for uf in sorted(uf_est, key=lambda x: -uf_est[x]):
    pessoas = sum(1 for (u,c) in uf_pessoas if u == uf)
    print(f"  {uf}: {uf_est[uf]} estacoes, {pessoas} pessoas, razao {uf_est[uf]/pessoas:.2f}")

# --- validade vencida: perfil ---
venc = [r for r in rows if r["Status da Validade"].strip() == "Vencida"]
print(f"\n=== Vencidas: {len(venc)} ===")
print("  por classe:", dict(collections.Counter(r['COER'] for r in venc)))
print("  por tipo:", dict(collections.Counter(r['Tipo de Estação'] for r in venc)))
print("  por UF (top):", collections.Counter(r['UF da Entidade'] for r in venc).most_common(8))
