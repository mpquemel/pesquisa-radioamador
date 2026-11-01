#!/usr/bin/env python3
"""exp_02 - decomposicao numerica exata do misterio dos indicativos."""
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

# Para cada CPF, quantos indicativos distintos tem
cpf_to_ind = collections.defaultdict(set)
for r in rows:
    c = cp(r); i = ind(r)
    if c and i: cpf_to_ind[c].add(i)

# distribuicao: quantos cpfs tem 1, 2, 3... indicativos
dist = collections.Counter(len(v) for v in cpf_to_ind.values())
print("distribuicao CPF -> N indicativos distintos:")
for n in sorted(dist):
    print(f"  {n} indicativo(s): {dist[n]} CPFs")

total_ind_via_cpf = sum(len(v) for v in cpf_to_ind.values())
print("\nsoma de indicativos distintos por CPF:", total_ind_via_cpf)

# Os 13 indicativos com multiplos CPFs: explicam quanto da diferenca?
# 46670 - 35498 = 11172
print("\nDiferenca indicativos - CPFs =", 46670 - 35498)

# indicativos totais (distintos) = soma. Vamos checar identidade:
# cada indicativo unico pertence a >=1 cpf. Se soma(len(v)) != 46670,
# entao ha indicativos que nao aparecem em nenhum cpf (mas vimos = 0).
print("indicativos distintos (soma por cpf):", total_ind_via_cpf)

# Verificar: ha indicativo associado a mais de um cpf (os 13) -> conta duplicada?
# O total de indicativos unicos = 46670. Se somamos len(v) por cpf, indicativos
# compartilhados sao contados 2x. Entao soma pode > 46670.
print("\nindicativos compartilhados entre cpfs:", sum(1 for v in cpf_to_ind.values() if len(v)>1))

# Decomposicao alternativa: indicativo -> numero de linhas
ind_linhas = collections.Counter()
for r in rows:
    if ind(r): ind_linhas[ind(r)] += 1

# indicativos que aparecem em 1 linha vs >1
sing = sum(1 for v in ind_linhas.values() if v == 1)
mult = sum(1 for v in ind_linhas.values() if v > 1)
print(f"\nindicativos em 1 linha: {sing}")
print(f"indicativos em >1 linhas: {mult}")
print(f"total indicativos distintos: {sing+mult}")

# Quantos CPFs tem exatamente 1 indicativo mas esse indicativo repete em varias linhas
# (fixa+movel do mesmo indicativo)
# Quantos indicativos tem >1 linha?
print("\nindicativos com >1 linha (fixa+movel etc):", mult)

# relacao: indicativo unico vs cpf unico
# 46670 - 35498 = 11172. De onde vem?
# Vamos medir: CPFs com >=2 indicativos distintos
cpf_2plus = sum(1 for v in cpf_to_ind.values() if len(v) >= 2)
print("\nCPFs com >=2 indicativos distintos:", cpf_2plus)
extra = sum(len(v)-1 for v in cpf_to_ind.values() if len(v) > 1)
print("soma (len-1) para cpfs multi-indicativo:", extra)

# indicativos compartilhados (mesmo indicativo em 2 cpfs diferentes)
shared = collections.defaultdict(set)
for r in rows:
    c = cp(r); i = ind(r)
    if c and i: shared[i].add(c)
n_shared = sum(1 for v in shared.values() if len(v) > 1)
print("indicativos em >1 CPF (compartilhados):", n_shared)
extra_shared = sum(len(v)-1 for v in shared.values() if len(v) > 1)
print("excesso por compartilhamento:", extra_shared)

print("\n=== CONTA FECHANDO ===")
print("46670 = 35498 + extra_multiindicativo - compartilhados?")
print(f"35498 + {extra} - {extra_shared} = {35498 + extra - extra_shared}")
