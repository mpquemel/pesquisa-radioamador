# PATCH-02 — Bug crítico: --classe, --tipo, --status sozinhos caem no modo interativo
#
# Arquivo: scripts/consultar.py
# Linha: 383-385 (predicado do modo interativo em `main`)
#
# Defeito: a condição que decide entrar no modo interativo olha apenas para
#   args.nome, args.cpf, args.fistel, args.municipio, args.uf, args.resumo_uf_flag
# e NÃO para args.classe, args.tipo, args.status. Resultado:
#
#   $ python3 scripts/consultar.py --classe A
#   ... entra no MODO INTERATIVO, ignorando o filtro
#
# Também afeta --status Vencida, --tipo Móvel, e combinações que não usem
# indicativo/nome/cpf/fistel/municipio/uf. O usuário acha que o filtro foi
# aceito; na verdade foi descartado em silêncio.
#
# Reproduzir:
#   python3 scripts/consultar.py --classe A
#   python3 scripts/consultar.py --status Vencida
#
# Correção: incluir os três flags no teste.

# --- ANTES ---
#     if args.indicativo == "__INTERATIVO__" or (
#             not any([args.nome, args.cpf, args.fistel, args.municipio,
#                      args.uf, args.resumo_uf_flag]) and not args.indicativo):
#         return interativo(args)

# --- DEPOIS ---
#     filtros_usados = [args.nome, args.cpf, args.fistel, args.municipio,
#                       args.uf, args.classe, args.tipo, args.status,
#                       args.resumo_uf_flag]
#     if args.indicativo == "__INTERATIVO__" or (
#             not any(filtros_usados) and not args.indicativo):
#         return interativo(args)
