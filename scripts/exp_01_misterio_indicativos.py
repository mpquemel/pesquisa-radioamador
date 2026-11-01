#!/usr/bin/env python3
"""exp_01 - decompor o misterio 46.670 indicativos vs 35.498 CPFs."""
import csv, collections
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "dados" / "Estacoes_Radioamador.csv"

rows = []
with open(CSV, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        rows.append(r)

print("total linhas:", len(rows))

# normalizar
def cp(r): return (r["CNPJ ou CPF"] or "").strip()
def ind(r): return (r["Indicativo"] or "").strip()
def tdoc(r): return (r["Tipo de Identificação"] or "").strip()

cpfs = collections.Counter()
inds = collections.Counter()
ind_to_cpf = collections.defaultdict(set)   # indicativo -> conjunto de cpfs
cpf_to_ind = collections.defaultdict(set)   # cpf -> conjunto de indicativos

for r in rows:
    c = cp(r); i = ind(r)
    if c: cpfs[c] += 1
    if i: inds[i] += 1
    if i and c:
        ind_to_cpf[i].add(c)
        cpf_to_ind[c].add(i)

print("\nCPFs distintos:", len(cpfs))
print("Indicativos distintos:", len(inds))

# indicativos sem CPF
ind_sem_cpf = [i for i in inds if i not in ind_to_cpf]
print("\nindicativos SEM nenhum CPF associado:", len(ind_sem_cpf))

# indicativos com multiplos cpfs (um indicativo usado por >1 documento)
ind_multicpf = {i: s for i, s in ind_to_cpf.items() if len(s) > 1}
print("indicativos com MULTIPLOS CPFs:", len(ind_multicpf))

# CPFs com multiplos indicativos
cpf_multiind = {c: s for c, s in cpf_to_ind.items() if len(s) > 1}
print("CPFs com MULTIPLOS indicativos:", len(cpf_multiind))

# distribuicao indicativo repetido em linhas
print("\n--- indicativo repetido em N linhas (top) ---")
reps = collections.Counter(inds.values())
for n in sorted(reps, reverse=True)[:10]:
    print(f"  {reps[n]} indicativos aparecem em {n} linhas")

# exemplos
print("\n--- exemplos: indicativo com multiplos CPFs ---")
for i in list(ind_multicpf)[:5]:
    print(f"  {i}: {len(ind_multicpf[i])} cpfs -> {sorted(ind_multicpf[i])[:3]}")

print("\n--- exemplos: CPF com multiplos indicativos (top 10) ---")
for c in sorted(cpf_multiind, key=lambda x: -len(cpf_multiind[x]))[:10]:
    print(f"  {c}: {len(cpf_multiind[c])} indicativos -> {sorted(cpf_multiind[c])[:5]}")

# indicativos que sao de CNPJ (entidade coletiva)
print("\n--- tipo de identificacao por indicativo ---")
# um indicativo pode estar em linha CPF e linha CNPJ?
ind_tdocs = collections.defaultdict(set)
for r in rows:
    if ind(r): ind_tdocs[ind(r)].add(tdoc(r))
mixed = {i: t for i, t in ind_tdocs.items() if len(t) > 1}
print("indicativos com tipo de doc misto (CPF e CNPJ):", len(mixed))
for i in list(mixed)[:5]:
    print(f"  {i}: {mixed[i]}")

# indicativo com CPF vazio mas presente em linhas
print("\n--- indicativos vazios ---")
print("linhas sem indicativo:", sum(1 for r in rows if not ind(r)))
print("linhas sem CPF:", sum(1 for r in rows if not cp(r)))
