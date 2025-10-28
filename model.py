import numpy as np
from gurobipy import GRB, Model
from converter import *

model = Model()

# Variables

s = model.addVars(N, range(T), vtype=GRB.BINARY, name="s")
u = model.addVars(N, K, range(T), vtype=GRB.INTEGER, name="u")
u_ = model.addVars(N, K, range(T), vtype=GRB.INTEGER, name="u_")
y = model.addVars(N, P, range(T), vtype=GRB.BINARY, name="y")
a = model.addVars(N, P, range(T), vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="a")
v = model.addVars(N, range(T), vtype=GRB.CONTINUOUS, lb=0.0, name="v")
z = model.addVars(P, range(T), vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z")
o = model.addVars(N, range(T), vtype=GRB.BINARY, name="o")
model.update()

# Restricciones

# R1 pendiente

model.addConstrs(
    (o[i, t] <= s[i, t] for i in N for t in range(T)),
    name="R2.1")

model.addConstrs(
    (s[i, t] - s[i, t-1] <= o[i, t] for i in N for t in range(1, T)),
    name="R2.2.1")

model.addConstrs(
    (s[i, 0] == 0 for i in N),
    name="R2.2.2")

model.addConstrs(
    (sum(u_[i, k, t] for k in K) <= U_MAX[i] for i in N for t in range(T)),
    name="R3")

model.addConstrs(
    (sum(Pot[k] * u_[i, k, t] for k in K) <= G[i][t] * s[i, t] for i in N for t in range(T)),
    name="R4")

model.addConstrs()