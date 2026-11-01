#!/usr/bin/env python3
"""exp_03 - exemplos reais + relacao Fistel/Estacao/Indicativo + chave primaria."""
import csv, collections
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
def fistel(r): return (r["Fistel do Serviço da Estação"] or "").strip()

cpf_to_ind = collections.defaultdict(set)
cpf_rows = collections.defaultdict(list)
for r in rows:
    c = cp(r)
    if c: cpf_to_ind[c].add(ind(r)); cpf_rows[c].append(r)

# 1. exemplo: CPF com 2 indicativos distintos (fixa + movel = indicativos diferentes?)
print("=== CPF com 2 indicativos distintos (exemplo) ===")
for c in cpf_to_ind:
    if len(cpf_to_ind[c]) == 2:
        for r in cpf_rows[c]:
            print(f"  {c} | ind={ind(r)} | tipo={r['Tipo de Estação']} | est={est(r)} | fistel={fistel(r)}")
        break

# 2. exemplo: CPF com 1 indicativo, mas 2 linhas (fixa+movel MESMO indicativo)
print("\n=== CPF com 1 indicativo mas 2 linhas (fixa+movel) ===")
for c in cpf_to_ind:
    if len(cpf_to_ind[c]) == 1 and len(cpf_rows[c]) == 2:
        for r in cpf_rows[c]:
            print(f"  {c} | ind={ind(r)} | tipo={r['Tipo de Estação']} | est={est(r)} | fistel={fistel(r)}")
        break

# 3. indicativo compartilhado (13 casos) - exemplo
shared = collections.defaultdict(set)
for r in rows:
    c = cp(r); i = ind(r)
    if c and i: shared[i].add(c)
shared_list = [i for i in shared if len(shared[i]) > 1]
print(f"\n=== indicativo compartilhado por 2 CPFs ({len(shared_list)} casos) exemplo ===")
for i in shared_list[:3]:
    print(f"  indicativo {i}: cpfs = {sorted(shared[i])}")
    for r in rows:
        if ind(r) == i:
            print(f"    {cp(r)} | tipo={r['Tipo de Estação']} | est={est(r)} | fistel={fistel(r)} | nome={r['Nome da Entidade']}")

# 4. CPF com mais indicativos (outlier) - top
print("\n=== CPFs com mais indicativos distintos (top 8) ===")
for c in sorted(cpf_to_ind, key=lambda x: -len(cpf_to_ind[x]))[:8]:
    n = len(cpf_to_ind[c])
    nome = cpf_rows[c][0]["Nome da Entidade"]
    print(f"  {c} ({nome}): {n} indicativos")

# 5. relacao Fistel -> numero de estacoes
fistel_est = collections.defaultdict(set)
fistel_ind = collections.defaultdict(set)
for r in rows:
    f = fistel(r)
    if f: fistel_est[f].add(est(r)); fistel_ind[f].add(ind(r))

print("\n=== Fistel: quantos numeros de estacao / indicativos ===")
dist_fistel = collections.Counter(len(v) for v in fistel_est.values())
print("Fistel -> N numeros de estacao:", dict(sorted(dist_fistel.items())))
dist_fistel_ind = collections.Counter(len(v) for v in fistel_ind.values())
print("Fistel -> N indicativos:", dict(sorted(dist_fistel_ind.items())))
print("Fistels distintos:", len(fistel_est))

# 6. chave primaria: Número da Estação - unico?
est_count = collections.Counter(est(r) for r in rows if est(r))
dup_est = [e for e, n in est_count.items() if n > 1]
print(f"\n=== Numero da Estacao ===")
print("numeros de estacao distintos:", len(est_count))
print("numeros de estacao duplicados:", len(dup_est), "->", dup_est[:5])

# 7. indicativo -> numero de estacoes (indicativo pode ter varias estacoes)
ind_est = collections.defaultdict(set)
for r in rows:
    if ind(r): ind_est[ind(r)].add(est(r))
dist_ind_est = collections.Counter(len(v) for v in ind_est.values())
print("\n=== Indicativo -> N numeros de estacao ===")
print(dict(sorted(dist_ind_est.items())))

# 8. CPF -> numeros de estacao (total de estacoes por pessoa)
cpf_est = collections.defaultdict(set)
for r in rows:
    if cp(r): cpf_est[cp(r)].add(est(r))
dist_cpf_est = collections.Counter(len(v) for v in cpf_est.values())
print("\n=== CPF -> N estacoes (top da distribuicao) ===")
for n in sorted(dist_cpf_est, reverse=True)[:15]:
    print(f"  {n} estacoes: {dist_cpf_est[n]} CPFs")
