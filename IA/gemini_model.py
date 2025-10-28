# main.py
# Entrypoint obligatorio para la Entrega 3
# Requisitos: pandas, numpy, gurobipy
# Ejecutar: python main.py

import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB
from collections import defaultdict

# -------------------------
# 0) CONFIG / Rutas datos
# -------------------------
DATA_DIR = "DATA/"
OUT_DIR  = "OUTPUT/"

# CSV esperados (ver instrucciones en el README de datos)
FILES = {
    "nodes": DATA_DIR + "nodes.csv",
    "routes": DATA_DIR + "routes.csv",
    "chargers": DATA_DIR + "chargers.csv",
    "windows": DATA_DIR + "windows.csv",
    "A_ip": DATA_DIR + "A_ip.csv",
    "D_p_t": DATA_DIR + "D_p_t.csv",
    "CFIX_i_t": DATA_DIR + "CFIX_i_t.csv",
    "CVAR_i_k_t": DATA_DIR + "CVAR_i_k_t.csv",
    "G_i_t": DATA_DIR + "G_i_t.csv",
    "Umax_i": DATA_DIR + "Umax_i.csv",
    "B_t": DATA_DIR + "B_t.csv",
    "INSTMAX_i_t": DATA_DIR + "INSTMAX_i_t.csv",
    "MFIX_i_t": DATA_DIR + "MFIX_i_t.csv",
    "MVAR_k_t": DATA_DIR + "MVAR_k_t.csv",
    "PHIeff_i_k_t": DATA_DIR + "PHIeff_i_k_t.csv",
    "mMIN_i_t": DATA_DIR + "mMIN_i_t.csv",
    "W_PRIOR_p": DATA_DIR + "W_PRIOR_p.csv",
    "omega_t": DATA_DIR + "omega_t.csv"
}

# -------------------------
# 1) CARGA DATOS
# -------------------------
def load_data():
    # simple wrappers that give helpful errors if file missing
    def r(fname):
        try:
            return pd.read_csv(FILES[fname])
        except Exception as e:
            raise FileNotFoundError(f"Falta archivo {FILES[fname]} (clave {fname}) - {e}")

    nodes_df = r("nodes")
    routes_df = r("routes")
    chargers_df = r("chargers")
    windows_df = r("windows")
    A_df = r("A_ip")
    D_df = r("D_p_t")
    CFIX_df = r("CFIX_i_t")
    CVAR_df = r("CVAR_i_k_t")
    G_df = r("G_i_t")
    Umax_df = r("Umax_i")
    B_df = r("B_t")
    INSTMAX_df = r("INSTMAX_i_t")
    MFIX_df = r("MFIX_i_t")
    MVAR_df = r("MVAR_k_t")
    PHIeff_df = r("PHIeff_i_k_t")
    mMIN_df = r("mMIN_i_t")
    Wprior_df = r("W_PRIOR_p")
    omega_df = r("omega_t")

    return {
        "nodes": nodes_df, "routes": routes_df, "chargers": chargers_df,
        "windows": windows_df, "A": A_df, "D": D_df, "CFIX": CFIX_df,
        "CVAR": CVAR_df, "G": G_df, "Umax": Umax_df, "B": B_df,
        "INSTMAX": INSTMAX_df, "MFIX": MFIX_df, "MVAR": MVAR_df,
        "PHIeff": PHIeff_df, "mMIN": mMIN_df, "Wprior": Wprior_df,
        "omega": omega_df
    }

data = load_data()

# -------------------------
# 2) Construcción conjuntos y parámetros (dicts)
# -------------------------
N = data["nodes"]["node_id"].astype(str).tolist()
P = data["routes"]["route_id"].astype(str).tolist()
K = data["chargers"]["charger_type"].astype(str).tolist()
KV2G = data["chargers"].loc[data["chargers"]["is_v2g"] == 1, "charger_type"].astype(str).tolist()

# years: tomar del D_p_t (asegúrate consistencia)
years = sorted(data["D"]["year"].unique().tolist())

# windows: dict route -> dict(window -> list(nodes))
windows = defaultdict(lambda: defaultdict(list))
for _, r in data["windows"].iterrows():
    windows[str(r["route_id"])][str(r["window_id"])].append(str(r["node_id"]))

# helpers: create lookup dicts (tuplas como claves)
def df_to_dict(df, keys, value_col):
    return {tuple([str(row[k]) for k in keys]): row[value_col] for _, row in df.iterrows()}

# A_ip
A = {(str(row["node_id"]), str(row["route_id"])): int(row["A"]) for _, row in data["A"].iterrows()}

# D_p_t
D = {(str(row["route_id"]), int(row["year"])): float(row["D"]) for _, row in data["D"].iterrows()}

# CFIX
CFIX = {(str(row["node_id"]), int(row["year"])): float(row["CFIX"]) for _, row in data["CFIX"].iterrows()}

# CVAR
CVAR = {(str(row["node_id"]), str(row["charger_type"]), int(row["year"])): float(row["CVAR"])
        for _, row in data["CVAR"].iterrows()}

# G
G = {(str(row["node_id"]), int(row["year"])): float(row["G_kW"]) for _, row in data["G"].iterrows()}

# Umax
Umax = {str(row["node_id"]): int(row["Umax"]) for _, row in data["Umax"].iterrows()}

# B
B = {int(row["year"]): float(row["B"]) for _, row in data["B"].iterrows()}

# INSTMAX
INSTMAX = {(str(row["node_id"]), int(row["year"])): int(row["INSTMAX"]) for _, row in data["INSTMAX"].iterrows()}

# MFIX, MVAR
MFIX = {(str(row["node_id"]), int(row["year"])): float(row["MFIX"]) for _, row in data["MFIX"].iterrows()}
MVAR = {(str(row["charger_type"]), int(row["year"])): float(row["MVAR"]) for _, row in data["MVAR"].iterrows()}

# PHIeff
PHIeff = {(str(row["node_id"]), str(row["charger_type"]), int(row["year"])): float(row["PHIeff"])
          for _, row in data["PHIeff"].iterrows()}

# mMIN
mMIN = {(str(row["node_id"]), int(row["year"])): int(row["mMIN"]) for _, row in data["mMIN"].iterrows()}

# W_PRIOR
W_PRIOR = {str(row["route_id"]): float(row["W"]) for _, row in data["Wprior"].iterrows()}

# omega
omega = {int(row["year"]): float(row["omega"]) for _, row in data["omega"].iterrows()}

# charger attributes
CAP = {str(row["charger_type"]): float(row["CAP_k"]) for _, row in data["chargers"].iterrows()}
P_k = {str(row["charger_type"]): float(row["P_k"]) for _, row in data["chargers"].iterrows()}
L_k = {str(row["charger_type"]): int(row["L_k"]) for _, row in data["chargers"].iterrows()}

# -------------------------
# 3) Crear modelo Gurobi
# -------------------------
model = gp.Model("EV_Planning_E3")

# Variables
s = model.addVars(N, years, vtype=GRB.BINARY, name="s")       # estado
o = model.addVars(N, years, vtype=GRB.BINARY, name="o")       # apertura
u = model.addVars(N, K, years, vtype=GRB.INTEGER, lb=0, name="u")      # instalacion (anual)
ubar = model.addVars(N, K, years, vtype=GRB.INTEGER, lb=0, name="ubar")# acumulado (vida util)
a = model.addVars(N, P, years, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="a")
z = model.addVars(P, years, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="z")
v_v2g = model.addVars(N, years, vtype=GRB.CONTINUOUS, lb=0, name="v")  # energia V2G

# (opcional) h binary for threshold services (no obligatorio)
h = model.addVars(N, years, vtype=GRB.BINARY, name="h")

# -------------------------
# 4) Restricciones
# -------------------------
# (1) acumulación con vida útil(sum móvil)
for i in N:
    for k in K:
        L = L_k[k]
        for t in years:
            start = max(min(years), t - L + 1)
            model.addConstr(ubar[i, k, t] == gp.quicksum(u[i, k, tau] for tau in years if start <= tau <= t),
                            name=f"accu_{i}{k}{t}")

# (2) apertura <-> estado
for i in N:
    for t in years:
        model.addConstr(o[i, t] <= s[i, t], name=f"open_le_state_{i}_{t}")
        if t == min(years):
            model.addConstr(s[i, t] - 0 <= o[i, t], name=f"open_first_{i}_{t}")
        else:
            prev = years[years.index(t) - 1]
            model.addConstr(s[i, t] - s[i, prev] <= o[i, t], name=f"open_vinc_{i}_{t}")

# (3) capacidad fisica
for i in N:
    for t in years:
        model.addConstr(gp.quicksum(ubar[i, k, t] for k in K) <= Umax.get(i, 10**6), name=f"umax_{i}_{t}")

# (4) limite potencia
for i in N:
    for t in years:
        Gval = G.get((i, t), 0.0)
        model.addConstr(gp.quicksum(P_k[k] * ubar[i, k, t] for k in K) <= Gval * s[i, t],
                        name=f"powlim_{i}_{t}")

# (5) limite instalaciones anuales
for i in N:
    for t in years:
        instmax = INSTMAX.get((i, t), 10**6)
        model.addConstr(gp.quicksum(u[i, k, t] for k in K) <= instmax, name=f"instmax_{i}_{t}")

# (6) presupuesto anual
for t in years:
    cost_op = gp.quicksum(MFIX.get((i, t), 0.0) * s[i, t] for i in N) + \
              gp.quicksum(MVAR.get((k, t), 0.0) * ubar[i, k, t] for i in N for k in K)
    invest = gp.quicksum(CFIX.get((i, t), 0.0) * o[i, t] for i in N) + \
             gp.quicksum(CVAR.get((i, k, t), 0.0) * u[i, k, t] for i in N for k in K)
    model.addConstr(invest + cost_op <= B.get(t, 0.0), name=f"budget_{t}")

# (7) elegibilidad y asignacion fraccionada
for p in P:
    for t in years:
        model.addConstr(gp.quicksum(a[i, p, t] for i in N) == z[p, t], name=f"assignsum_{p}_{t}")
        for i in N:
            Aip = A.get((i, p), 0)
            model.addConstr(a[i, p, t] <= Aip * s[i, t], name=f"elig_{i}{p}{t}")
for i in N:
    for t in years:
        model.addConstr(gp.quicksum(D.get((p, t), 0.0) * a[i, p, t] for p in P) <=
                        gp.quicksum(CAP[k] * ubar[i, k, t] for k in K), name=f"capacity_assign_{i}_{t}")

# (8) ventanas: cobertura final
Tfinal = max(years)
for p in P:
    for w in windows[p].keys():
        model.addConstr(gp.quicksum(s[i, Tfinal] for i in windows[p][w]) >= 1, name=f"window_final_{p}_{w}")

# (9) V2G limitado por PHIeff (solo suma sobre KV2G)
for i in N:
    for t in years:
        model.addConstr(v_v2g[i, t] <= gp.quicksum(PHIeff.get((i, k, t), 0.0) * ubar[i, k, t] for k in KV2G),
                        name=f"v2glimit_{i}_{t}")

# (11) min V2G por estacion (si aplica)
for i in N:
    for t in years:
        model.addConstr(gp.quicksum(ubar[i, k, t] for k in KV2G) >= mMIN.get((i, t), 0) * s[i, t],
                        name=f"min_v2g_{i}_{t}")

# -------------------------
# 5) OBJETIVO
# -------------------------
# cobertura ponderada + beneficio por V2G (omega_t * v)
obj_coverage = gp.quicksum(W_PRIOR.get(p, 0.0) * D.get((p, t), 0.0) * z[p, t] for p in P for t in years)
obj_v2g = gp.quicksum(omega.get(t, 0.0) * v_v2g[i, t] for i in N for t in years)
model.setObjective(obj_coverage + obj_v2g, GRB.MAXIMIZE)

# -------------------------
# 6) PARAMS SOLVER y OPTIMIZAR
# -------------------------
model.Params.TimeLimit = 1800           # 30 minutos exigidos por la pauta
model.Params.MIPGap = 1e-4
# model.Params.Threads = 4              # opcional: fijar nº threads

model.optimize()

# -------------------------
# 7) Guardar resultados legibles
# -------------------------
import os
os.makedirs(OUT_DIR, exist_ok=True)

def save_var_table(var, keys, name, cast=int):
    rows = []
    for key in keys:
        try:
            val = var[key].X
        except Exception:
            val = None
        rows.append(dict(zip(keys[0]._fields, key) if hasattr(keys[0], "_fields") else {"key": key, "val": val}))
    # fallback: create DataFrame with tuples
    df = []
    for k, v in var.items():
        df.append({"index": k, "value": (int(v.X) if v.X is not None and (v.VType in (GRB.BINARY, GRB.INTEGER)) else v.X)})
    pd.DataFrame(df).to_csv(OUT_DIR + f"{name}.csv", index=False)

# Simple saving of selected variables
rows = []
for i in N:
    for t in years:
        rows.append({"node": i, "year": t, "s": int(s[i,t].X), "o": int(o[i,t].X),
                     "v2g": float(v_v2g[i,t].X)})
pd.DataFrame(rows).to_csv(OUT_DIR + "stations_solution.csv", index=False)

rows_u = []
for i in N:
    for k in K:
        for t in years:
            rows_u.append({'node': i, 'charger': k, 'year': t, 'ubar': int(ubar[i,k,t].X)})
pd.DataFrame(rows_u).to_csv(OUT_DIR + "chargers_accumulated.csv", index=False)

rows_a = []
for p in P:
    for t in years:
        rows_a.append({'route': p, 'year': t, 'z': float(z[p,t].X)})
pd.DataFrame(rows_a).to_csv(OUT_DIR + "route_coverage.csv", index=False)

print("Finished. Status:", model.Status)
print("Objective:", model.ObjVal if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT else None)