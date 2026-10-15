"""Exporta os microdados do Novo CAGED para uso em Power BI e Looker Studio.

Gera um modelo estrela (dimensões + fato) em dois formatos:
  dados/power_bi_export/powerbi/  -> CSV separado por ';', decimal ',', UTF-8 com BOM
  dados/power_bi_export/looker/   -> CSV separado por ',', decimal '.', UTF-8

Arquivos gerados por pasta:
  dim_municipio.csv, dim_secao.csv, dim_sexo.csv, dim_raca_cor.csv,
  dim_grau_instrucao.csv, dim_faixa_etaria.csv, dim_tipo_movimentacao.csv,
  dim_categoria.csv, dim_tamanho_estabelecimento.csv, dim_ocupacao.csv,
  dim_tipo_deficiencia.csv
  fato_movimentacoes.csv   (microdados decodificados, grão = registro)
  fato_agregado.csv        (cubo pré-agregado para painéis rápidos)
"""
from __future__ import annotations

import json
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET = os.path.abspath(os.path.join(BASE_DIR, "..", "dados", "caged_baixada_202401.parquet"))
DICTS = os.path.join(BASE_DIR, "data", "dictionaries.json")
EXPORT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "dados", "power_bi_export"))

MUNICIPIO_NOMES = {
    "330045": "Belford Roxo", "330170": "Duque de Caxias", "330200": "Itaguaí",
    "330227": "Japeri", "330285": "Mesquita", "330320": "Nilópolis",
    "330350": "Nova Iguaçu", "330360": "Paracambi", "330414": "Queimados",
    "330430": "Rio Bonito", "330455": "Rio de Janeiro", "330490": "São Gonçalo",
}
BAIXADA = {"330045", "330170", "330200", "330227", "330285", "330320",
           "330350", "330360", "330414", "330490"}

FAIXAS = [(1, "10 a 14 anos", 0, 14), (2, "15 a 17 anos", 15, 17), (3, "18 a 24 anos", 18, 24),
          (4, "25 a 29 anos", 25, 29), (5, "30 a 39 anos", 30, 39), (6, "40 a 49 anos", 40, 49),
          (7, "50 a 64 anos", 50, 64), (8, "65 anos ou mais", 65, 200)]


def faixa_cod(idade):
    if pd.isna(idade):
        return 99
    for cod, _n, lo, hi in FAIXAS:
        if lo <= int(idade) <= hi:
            return cod
    return 99


def write_csv(df: pd.DataFrame, path: str, sep: str, decimal: str, encoding: str):
    df.to_csv(path, index=False, sep=sep, decimal=decimal, encoding=encoding, lineterminator="\n")
    size = os.path.getsize(path) / 1024
    print(f"  {os.path.relpath(path, EXPORT_ROOT):55s} {len(df):>8} linhas  {size:8.0f} KB")


def build_frames():
    with open(DICTS, encoding="utf-8") as f:
        dic = json.load(f)

    df = pd.read_parquet(PARQUET)

    col = lambda c: df[c].astype(str).str.strip()
    mun = col("municipio")
    secao = col("seçao")
    sexo = col("sexo")
    raca = col("raçacor")
    grau = col("graudeinstruçao")
    tipo = col("tipomovimentaçao")
    cat = col("categoria")
    tam = col("tamestabjan")
    pcd = col("tipodedeficiência")
    cbo = col("cbo2002ocupaçao")

    idade = pd.to_numeric(df["idade"], errors="coerce")
    sal = pd.to_numeric(df["valorsaláriofixo"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    horas = pd.to_numeric(df["horascontratuais"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    classe = col("saldomovimentaçao").map({"1": 0, "-1": 1})

    keep = classe.notna()
    mun, secao, sexo, raca, grau, tipo, cat, tam, pcd, cbo = (
        s[keep] for s in (mun, secao, sexo, raca, grau, tipo, cat, tam, pcd, cbo))
    idade, sal, horas, classe = idade[keep], sal[keep], horas[keep], classe[keep].astype(int)
    comp = col("competênciamov")[keep]

    nomes = lambda d, code: d.get(str(code), str(code))

    fato = pd.DataFrame({
        "competencia": comp.values,
        "municipio_codigo": mun.values,
        "municipio": [MUNICIPIO_NOMES.get(c, dic.get("municipio", {}).get(c, c)) for c in mun.values],
        "baixada_fluminense": ["Sim" if c in BAIXADA else "Não" for c in mun.values],
        "secao_codigo": secao.values,
        "secao": [nomes(dic["secao"], c) for c in secao.values],
        "subclasse_cnae": col("subclasse")[keep].values,
        "movimento": ["Admissao" if c == 0 else "Desligamento" for c in classe.values],
        "saldo": [1 if c == 0 else -1 for c in classe.values],
        "tipo_movimentacao_codigo": tipo.values,
        "tipo_movimentacao": [nomes(dic["tipomovimentacao"], c) for c in tipo.values],
        "cbo_codigo": cbo.values,
        "cbo_ocupacao": [nomes(dic["cbo2002ocupacao"], c) for c in cbo.values],
        "categoria_codigo": cat.values,
        "categoria": [nomes(dic["categoria"], c) for c in cat.values],
        "grau_instrucao_codigo": grau.values,
        "grau_instrucao": [nomes(dic["graudeinstrucao"], c) for c in grau.values],
        "idade": idade.round().astype("Int64").values,
        "faixa_etaria_codigo": idade.map(faixa_cod).astype(int).values,
        "horas_contratuais": horas.round().astype("Int64").values,
        "raca_cor_codigo": raca.values,
        "raca_cor": [nomes(dic["racacor"], c) for c in raca.values],
        "sexo_codigo": sexo.values,
        "sexo": [nomes(dic["sexo"], c) for c in sexo.values],
        "tipo_empregador": col("tipoempregador")[keep].values,
        "tipo_estabelecimento": col("tipoestabelecimento")[keep].values,
        "tipo_deficiencia_codigo": pcd.values,
        "tipo_deficiencia": [nomes(dic.get("tipodedeficiencia", {}), c) for c in pcd.values],
        "intermitente": (col("indtrabintermitente")[keep] == "1").astype(int).values,
        "trabalho_parcial": (col("indtrabparcial")[keep] == "1").astype(int).values,
        "aprendiz": (col("indicadoraprendiz")[keep] == "1").astype(int).values,
        "salario": sal.values,
        "tamanho_estabelecimento_codigo": tam.values,
        "tamanho_estabelecimento": [nomes(dic["tamestabjan"], c) for c in tam.values],
    })
    fato["faixa_etaria"] = fato["faixa_etaria_codigo"].map(
        {c: n for c, n, _l, _h in FAIXAS} | {99: "Nao Informado"})

    # cubo pre-agregado (grao = municipio x secao x sexo x faixa x movimento)
    g = fato.groupby(["municipio_codigo", "municipio", "baixada_fluminense",
                      "secao_codigo", "secao", "sexo_codigo", "sexo",
                      "faixa_etaria_codigo", "faixa_etaria", "movimento"], as_index=False).agg(
        registros=("saldo", "size"),
        salarios_validos=("salario", lambda s: int((s > 0).sum())),
        soma_salarios=("salario", lambda s: float(s[s > 0].sum())),
    )
    g["salario_medio"] = (g["soma_salarios"].astype(float) / g["salarios_validos"].astype(float).replace(0, pd.NA)).fillna(0.0).astype(float)

    dims = {
        "dim_municipio.csv": pd.DataFrame({
            "municipio_codigo": sorted(mun.unique()),
        }).assign(
            municipio=lambda d: d["municipio_codigo"].map(lambda c: MUNICIPIO_NOMES.get(c, dic.get("municipio", {}).get(c, c))),
            baixada_fluminense=lambda d: d["municipio_codigo"].map(lambda c: "Sim" if c in BAIXADA else "Nao"),
            regiao=lambda d: "Metropolitana do Rio de Janeiro",
        )[["municipio_codigo", "municipio", "baixada_fluminense", "regiao"]],
        "dim_secao.csv": pd.DataFrame({"secao_codigo": sorted(secao.unique())}).assign(
            secao=lambda d: d["secao_codigo"].map(lambda c: nomes(dic["secao"], c))),
        "dim_sexo.csv": pd.DataFrame({"sexo_codigo": sorted(sexo.unique())}).assign(
            sexo=lambda d: d["sexo_codigo"].map(lambda c: nomes(dic["sexo"], c))),
        "dim_raca_cor.csv": pd.DataFrame({"raca_cor_codigo": sorted(raca.unique())}).assign(
            raca_cor=lambda d: d["raca_cor_codigo"].map(lambda c: nomes(dic["racacor"], c))),
        "dim_grau_instrucao.csv": pd.DataFrame({"grau_instrucao_codigo": sorted(grau.unique(), key=lambda x: int(x) if x.isdigit() else 999)}).assign(
            grau_instrucao=lambda d: d["grau_instrucao_codigo"].map(lambda c: nomes(dic["graudeinstrucao"], c))),
        "dim_faixa_etaria.csv": pd.DataFrame({
            "faixa_etaria_codigo": [c for c, _n, _l, _h in FAIXAS] + ([99] if (fato["faixa_etaria_codigo"] == 99).any() else []),
        }).assign(faixa_etaria=lambda d: d["faixa_etaria_codigo"].map(
            {c: n for c, n, _l, _h in FAIXAS} | {99: "Nao Informado"})),
        "dim_tipo_movimentacao.csv": pd.DataFrame({"tipo_movimentacao_codigo": sorted(tipo.unique(), key=lambda x: int(x) if x.isdigit() else 999)}).assign(
            tipo_movimentacao=lambda d: d["tipo_movimentacao_codigo"].map(lambda c: nomes(dic["tipomovimentacao"], c))),
        "dim_categoria.csv": pd.DataFrame({"categoria_codigo": sorted(cat.unique(), key=lambda x: int(x) if x.isdigit() else 999)}).assign(
            categoria=lambda d: d["categoria_codigo"].map(lambda c: nomes(dic["categoria"], c))),
        "dim_tamanho_estabelecimento.csv": pd.DataFrame({"tamanho_estabelecimento_codigo": sorted(tam.unique(), key=lambda x: int(x) if x.isdigit() else 999)}).assign(
            tamanho_estabelecimento=lambda d: d["tamanho_estabelecimento_codigo"].map(lambda c: nomes(dic["tamestabjan"], c))),
        "dim_tipo_deficiencia.csv": pd.DataFrame({"tipo_deficiencia_codigo": sorted(pcd.unique())}).assign(
            tipo_deficiencia=lambda d: d["tipo_deficiencia_codigo"].map(lambda c: nomes(dic.get("tipodedeficiencia", {}), c))),
        "dim_ocupacao.csv": pd.DataFrame({"cbo_codigo": sorted(cbo.unique())}).assign(
            cbo_ocupacao=lambda d: d["cbo_codigo"].map(lambda c: nomes(dic["cbo2002ocupacao"], c))),
    }
    return dims, fato, g


def export(sep, decimal, encoding, folder):
    out = os.path.join(EXPORT_ROOT, folder)
    os.makedirs(out, exist_ok=True)
    print(f"\n[{folder}]  separador='{sep}'  decimal='{decimal}'  encoding={encoding}")
    dims, fato, agg = build_frames()
    for name, d in dims.items():
        write_csv(d, os.path.join(out, name), sep, decimal, encoding)
    write_csv(fato, os.path.join(out, "fato_movimentacoes.csv"), sep, decimal, encoding)
    write_csv(agg, os.path.join(out, "fato_agregado.csv"), sep, decimal, encoding)


def main():
    os.makedirs(EXPORT_ROOT, exist_ok=True)
    export(";", ",", "utf-8-sig", "powerbi")
    export(",", ".", "utf-8", "looker")
    print(f"\nConcluido. Arquivos em {EXPORT_ROOT}")


if __name__ == "__main__":
    main()
