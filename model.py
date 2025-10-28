import numpy as np
from gurobipy import GRB, Model
from converter import *

model = Model()

# Variables

s = model.addVars(N, T, vtype=GRB.BINARY, name="s")
u = model.addVars(N, K, T, vtype=GRB.INTEGER, name="u")
u_ = model.addVars(N, K, T, vtype=GRB.INTEGER, name="u_")
y = model.addVars(N, P, T, vtype=GRB.BINARY, name="y")
a = model.addVars(N, P, T, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="a")
v = model.addVars(N, T, vtype=GRB.CONTINUOUS, lb=0.0, name="v")
z = model.addVars(P, T, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z")
o = model.addVars(N, T, vtype=GRB.BINARY, name="o")
model.update()

# Restricciones
