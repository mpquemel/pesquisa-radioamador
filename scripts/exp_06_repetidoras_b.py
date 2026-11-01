#!/usr/bin/env python3
"""exp_06 - as 35 repetidoras Classe B: datas, para saber se anteriores a Res 449/2006."""
import csv, collections, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "dados" / "Estacoes_Radioamador.csv"
rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig"), delimiter=";"))

rep_b = [r for r in rows if r["Tipo de Estação"].strip()=="Repetidora" and r["COER"].strip()=="Classe B"]
print(f"Repetidoras Classe B: {len(rep_b)}")
print("\n=== Datas de primeiro licenciamento ===")
anos = collections.Counter()
for r in rep_b:
    d = r["Data do Primeiro Licenciamento"].strip()
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', d)
    ano = m.group(3) if m else "??"
    anos[ano] += 1
    print(f"  {r['Indicativo']:8s} | {r['Nome da Entidade']:40s} | 1ºlic={d} | UF={r['UF da Entidade']} | doc={r['CNPJ ou CPF']}")
print("\nAnos:", dict(sorted(anos.items())))

# e as repetidoras Classe A: quando? distribuicao de ano
rep_a = [r for r in rows if r["Tipo de Estação"].strip()=="Repetidora" and r["COER"].strip()=="Classe A"]
anos_a = collections.Counter()
for r in rep_a:
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', r["Data do Primeiro Licenciamento"].strip())
    anos_a[m.group(3) if m else "??"] += 1
print(f"\nRepetidoras Classe A: {len(rep_a)}")
print("Anos Classe A:", dict(sorted(anos_a.items())))
