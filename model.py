import numpy as np
from gurobipy import GRB, Model, quicksum
from converter import *

model = Model("EV_Charging_Chile_V2G")

# Variables

s = model.addVars(N, period, vtype=GRB.BINARY, name="s")
u = model.addVars(N, K, period, vtype=GRB.INTEGER, name="u")
u_ = model.addVars(N, K, period, vtype=GRB.INTEGER, name="u_")
y = model.addVars(N, P, period, vtype=GRB.BINARY, name="y")
a = model.addVars(N, P, period, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="a")
v = model.addVars(N, period, vtype=GRB.CONTINUOUS, lb=0.0, name="v")
z = model.addVars(P, period, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z")
o = model.addVars(N, period, vtype=GRB.BINARY, name="o")
model.update()

# Restricciones

# R1: Acumulación con vida útil (suma móvil)
for i in N:
    for k in K:
        for t in period:
            start = max(0, t-L[k]+1)
            model.addConstr(u_[i, k, t] == quicksum(u[i, k, tau] for tau in period if start <= tau <= t),
                            name="R1")

# R2: Vinculación apertura / operación
model.addConstrs(
    (o[i, t] <= s[i, t] for i in N for t in period),
    name="R2.1")

model.addConstrs(
    (s[i, t] - s[i, t-1] <= o[i, t] for i in N for t in range(1, len(T))),
    name="R2.2.1")

model.addConstrs(
    (s[i, 0] == 0 for i in N),
    name="R2.2.2")

# R3: Capácidad física en nodo (acumulada)
model.addConstrs(
    (quicksum(u_[i, k, t] for k in K) <= U_MAX[i] for i in N for t in period),
    name="R3")

# R4: Límite de potencia (kW)
model.addConstrs(
    (quicksum(Pot[k] * u_[i, k, t] for k in K) <= G.get((i, t), 0) * s[i, t] for i in N for t in period),
    name="R4")

# R5: Límite de instalación por año (capacidad de ejecución)
model.addConstrs(
    (quicksum(u[i, k, t] for k in K) <= INST_MAX.get((i, t), 10**6)),
    name="R5")

# R6: Presupuesto anual (incluye operación y mantenimiento)
COST_OP = []
for t in period:
    COST_OP[t] = quicksum(M_FIX.get((i, t), 0) * s[i, t] for i in N) + quicksum(M_VAR.get((i, t), 0) * u_[i, k, t] for i in N for k in K)

model.addConstrs(
    (quicksum(C_FIX.get((i, t), 0) * o[i, t] for i in N) + quicksum(C_VAR.get((i, k, t), 0) for i in N for k in K) + COST_OP[t] <= B[t] for t in period),
    name="R6")

# R7: Elegibilidad y asignación fraccionada (sin doble conteo)
model.addConstrs(
    (0 <= a[i, p, t] <= A.get((i, p), 0) * s[i, t] for i in N for p in P for t in period),
    name="R7.1")

model.addConstrs(
    (quicksum(a[i, p, t] for i in N) == z[p, t] for p in P for t in period),
    name="R7.2")

model.addConstrs(
    (quicksum(D.get((p, t), 0) * a[i, p, t] for p in P) <= quicksum(CAP[k] * u_[i, k, t] for k in K) for i in N for t in period),
    name="R7.3")

# R8: Ventanas / autonomía (sin huecos) por año
model.addConstrs(
    (quicksum(s[i, 9] for i in N[w]) >= 1 for p in P for w in W[p]),
    name="R8")

# R9: V2G separado y limitado
model.addConstrs(
    (v[i, t] <= quicksum(Phi_eff.get((i, k, t), 0) * u_[i, k, t] for k in K_V2G) for i in N for t in period),
    name="R9")

# R10: Cobertura mínima (opcional)
# model.addConstrs(
#     (z[p, t] >= Z_MIN[p] for p in P_Crit)
#     ,name="R10")

# R11: Mínimo de cargadores V2G por estación
model.addConstrs(
    (quicksum(u_[i, k, t] for k in K_V2G) >= m_MIN.get((i, t), 0) * s[i, t] for i in N for t in period),
    name="R11")

# R12: Presupuesto para la compensación monetaria al usuario
model.addConstrs(
    (Sigma[t] * quicksum(v[i, t] for i in N) <= B_INC[t] for t in period),
    name="R12")

model.update()

# Función Objetivo
model.setObjective(
    quicksum(W_PRIOR[p] * D.get((p, t), 0) * z[p, t] for p in P for t in period) + quicksum(Omega[t] * quicksum(v[i, t] for i in N) for t in period),
    GRB.MAXIMIZE)
model.update()