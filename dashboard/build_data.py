"""Gera os agregados do dashboard a partir dos microdados do Novo CAGED.

Entrada:
  ../dados/caged_baixada_202401.parquet   (base tratada do projeto)
  ./data/dictionaries.json                (dicionários oficiais do MTE)

Saída:
  ./data/dashboard_data.json              (agregados consumidos pelo front-end)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET = os.path.abspath(os.path.join(BASE_DIR, "..", "dados", "caged_baixada_202401.parquet"))
DICTS = os.path.join(BASE_DIR, "data", "dictionaries.json")
OUT = os.path.join(BASE_DIR, "data", "dashboard_data.json")

MUNICIPIO_NOMES = {
    "330045": "Belford Roxo",
    "330170": "Duque de Caxias",
    "330200": "Itaguaí",
    "330227": "Japeri",
    "330285": "Mesquita",
    "330320": "Nilópolis",
    "330350": "Nova Iguaçu",
    "330360": "Paracambi",
    "330414": "Queimados",
    "330430": "Rio Bonito",
    "330455": "Rio de Janeiro",
    "330490": "São Gonçalo",
}

BAIXADA = {"330045", "330170", "330200", "330227", "330285", "330320",
           "330350", "330360", "330414", "330490"}

FAIXAS_ETARIAS = [
    (1, "10 a 14 anos", 0, 14),
    (2, "15 a 17 anos", 15, 17),
    (3, "18 a 24 anos", 18, 24),
    (4, "25 a 29 anos", 25, 29),
    (5, "30 a 39 anos", 30, 39),
    (6, "40 a 49 anos", 40, 49),
    (7, "50 a 64 anos", 50, 64),
    (8, "65 anos ou mais", 65, 200),
]


def _index(values):
    seen = {}
    order = []
    for v in values:
        if v not in seen:
            seen[v] = len(order)
            order.append(v)
    return seen, order


def classificar_faixa(idade):
    if pd.isna(idade):
        return 99
    for cod, _nome, lo, hi in FAIXAS_ETARIAS:
        if lo <= int(idade) <= hi:
            return cod
    return 99


def main():
    with open(DICTS, encoding="utf-8") as f:
        dic = json.load(f)

    df = pd.read_parquet(PARQUET)

    df["mun"] = df["municipio"].astype(str).str.strip()
    df["secao"] = df["seçao"].astype(str).str.strip()
    df["sexo"] = df["sexo"].astype(str).str.strip()
    df["raca"] = df["raçacor"].astype(str).str.strip()
    df["grau"] = df["graudeinstruçao"].astype(str).str.strip()
    df["tipomov"] = df["tipomovimentaçao"].astype(str).str.strip()
    df["idade_n"] = pd.to_numeric(df["idade"], errors="coerce")
    df["faixa"] = df["idade_n"].map(classificar_faixa).astype(str)

    sal = pd.to_numeric(df["valorsaláriofixo"].astype(str).str.replace(",", ".", regex=False),
                        errors="coerce")
    df["sal"] = sal.where(sal > 0, 0.0)  # ignora salários inválidos/zerados no somatório
    df["sal_ok"] = (sal > 0).astype(int)

    df["classe"] = df["saldomovimentaçao"].astype(str).str.strip().map({"1": 0, "-1": 1})
    df = df[df["classe"].notna()].copy()
    df["classe"] = df["classe"].astype(int)

    # dimensões
    mun_idx, mun_order = _index(sorted(df["mun"].unique()))
    sec_idx, sec_order = _index(sorted(df["secao"].unique()))
    sex_idx, sex_order = _index(sorted(df["sexo"].unique()))
    faixa_order = [str(c) for c, _n, _l, _h in FAIXAS_ETARIAS]
    if (df["faixa"] == "99").any():
        faixa_order.append("99")
    faixa_idx = {v: i for i, v in enumerate(faixa_order)}
    raca_idx, raca_order = _index(sorted(df["raca"].unique()))
    grau_order = sorted(df["grau"].unique(), key=lambda x: int(x) if x.isdigit() else 999)
    grau_idx = {v: i for i, v in enumerate(grau_order)}

    # códigos de desligamento presentes
    desl_codes = sorted([c for c in df["tipomov"].unique() if df.loc[df["tipomov"] == c, "classe"].iloc[0] == 1],
                        key=lambda x: int(x))
    desl_idx = {c: i for i, c in enumerate(desl_codes)}

    df["mi"] = df["mun"].map(mun_idx)
    df["si"] = df["secao"].map(sec_idx)
    df["xi"] = df["sexo"].map(sex_idx)
    df["fi"] = df["faixa"].map(faixa_idx)
    df["ri"] = df["raca"].map(raca_idx)
    df["gi"] = df["grau"].map(grau_idx)

    def agg(keys):
        g = df.groupby(keys, observed=True).agg(
            n=("classe", "size"), ns=("sal_ok", "sum"), sal=("sal", "sum"))
        return g.reset_index()

    # cubo principal: municipio x seção x sexo x faixa x classe
    c = agg(["mi", "si", "xi", "fi", "classe"])
    cube = [[int(r.mi), int(r.si), int(r.xi), int(r.fi), int(r.classe), int(r.n), int(r.ns), round(float(r.sal), 2)]
            for r in c.itertuples()]

    # raça: municipio x sexo x raça x classe
    c = agg(["mi", "xi", "ri", "classe"])
    raca = [[int(r.mi), int(r.xi), int(r.ri), int(r.classe), int(r.n), int(r.ns), round(float(r.sal), 2)]
            for r in c.itertuples()]

    # escolaridade: municipio x sexo x grau x classe
    c = agg(["mi", "xi", "gi", "classe"])
    grau = [[int(r.mi), int(r.xi), int(r.gi), int(r.classe), int(r.n), int(r.ns), round(float(r.sal), 2)]
            for r in c.itertuples()]

    # tipo de desligamento: municipio x sexo x tipo
    desl_df = df[df["classe"] == 1].copy()
    desl_df["ti"] = desl_df["tipomov"].map(desl_idx)
    c = desl_df.groupby(["mi", "xi", "ti"], observed=True).agg(
        n=("classe", "size"), ns=("sal_ok", "sum"), sal=("sal", "sum")).reset_index()
    desl = [[int(r.mi), int(r.xi), int(r.ti), int(r.n), int(r.ns), round(float(r.sal), 2)] for r in c.itertuples()]

    # ocupações (CBO) - top 30 global por volume de movimentação
    cbo_names = dic.get("cbo2002ocupacao", {})
    top = df["cbo2002ocupaçao"].astype(str).str.strip().value_counts().head(30).index.tolist()
    occ_idx = {code: i for i, code in enumerate(top)}
    occ_list = [{"code": code, "name": cbo_names.get(code, f"CBO {code}")} for code in top]
    cbo_df = df[df["cbo2002ocupaçao"].astype(str).str.strip().isin(top)].copy()
    cbo_df["ci"] = cbo_df["cbo2002ocupaçao"].astype(str).str.strip().map(occ_idx)
    cbo_df["adm"] = (cbo_df["classe"] == 0).astype(int)
    cbo_df["des"] = (cbo_df["classe"] == 1).astype(int)
    cbo_df["sadm"] = cbo_df["sal"].where(cbo_df["classe"] == 0, 0.0)
    cbo_df["sdes"] = cbo_df["sal"].where(cbo_df["classe"] == 1, 0.0)
    cbo_df["nadm"] = cbo_df["sal_ok"].where(cbo_df["classe"] == 0, 0)
    cbo_df["ndes"] = cbo_df["sal_ok"].where(cbo_df["classe"] == 1, 0)
    g = cbo_df.groupby(["mi", "xi", "ci"], observed=True).agg(
        adm=("adm", "sum"), des=("des", "sum"),
        sadm=("sadm", "sum"), sdes=("sdes", "sum"),
        nadm=("nadm", "sum"), ndes=("ndes", "sum"),
    ).reset_index()
    cbo = [[int(r.mi), int(r.xi), int(r.ci), int(r.adm), int(r.des),
            round(float(r.sadm), 2), round(float(r.sdes), 2), int(r.nadm), int(r.ndes)]
           for r in g.itertuples()]

    # flags (intermitente, parcial, aprendiz, pcd): municipio x sexo x classe
    for col, src in [("intermitente", "indtrabintermitente"), ("parcial", "indtrabparcial"),
                     ("aprendiz", "indicadoraprendiz"), ("pcd", "tipodedeficiência")]:
        if col == "pcd":
            df[col] = (df[src].astype(str).str.strip() != "0").astype(int)
        else:
            df[col] = (df[src].astype(str).str.strip() == "1").astype(int)
    g = df.groupby(["mi", "xi", "classe"], observed=True).agg(
        intermitente=("intermitente", "sum"), parcial=("parcial", "sum"),
        aprendiz=("aprendiz", "sum"), pcd=("pcd", "sum"),
        n=("classe", "size")).reset_index()
    flags = [[int(r.mi), int(r.xi), int(r.classe), int(r.intermitente), int(r.parcial),
              int(r.aprendiz), int(r.pcd), int(r.n)] for r in g.itertuples()]

    payload = {
        "meta": {
            "titulo": "Mercado de Trabalho Formal na Baixada Fluminense",
            "fonte": "Novo CAGED - Ministério do Trabalho e Emprego (MTE)",
            "competencia": str(df["competênciamov"].astype(str).str.strip().iloc[0]),
            "total_registros": int(len(df)),
            "admissoes": int((df["classe"] == 0).sum()),
            "desligamentos": int((df["classe"] == 1).sum()),
            "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        },
        "municipios": [{"code": code, "name": MUNICIPIO_NOMES.get(code, dic.get("municipio", {}).get(code, code)),
                        "baixada": code in BAIXADA} for code in mun_order],
        "secoes": [{"code": code, "name": dic.get("secao", {}).get(code, code)} for code in sec_order],
        "sexos": [{"code": code, "name": dic.get("sexo", {}).get(code, code)} for code in sex_order],
        "faixas": [{"code": code, "name": next((n for c, n, _l, _h in FAIXAS_ETARIAS if str(c) == code), "Não Informado")}
                   for code in faixa_order],
        "racas": [{"code": code, "name": dic.get("racacor", {}).get(code, code)} for code in raca_order],
        "graus": [{"code": code, "name": dic.get("graudeinstrucao", {}).get(code, code)} for code in grau_order],
        "tipos_desl": [{"code": code, "name": dic.get("tipomovimentacao", {}).get(code, f"Código {code}")}
                       for code in desl_codes],
        "ocupacoes": occ_list,
        "cube": cube,
        "raca": raca,
        "grau": grau,
        "desl": desl,
        "cbo": cbo,
        "flags": flags,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT) / 1024
    print(f"OK -> {OUT}  ({size:.0f} KB)")
    print(f"registros={len(df)}  admissoes={payload['meta']['admissoes']}  "
          f"desligamentos={payload['meta']['desligamentos']}  saldo={payload['meta']['admissoes']-payload['meta']['desligamentos']}")
    print(f"linhas: cube={len(cube)} raca={len(raca)} grau={len(grau)} desl={len(desl)} cbo={len(cbo)} flags={len(flags)}")


if __name__ == "__main__":
    main()
