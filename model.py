import numpy as np
from gurobipy import GRB, Model
from converter import *

model = Model()

# Variables
s = model.addVars(range(len(N)), range(len(T)), vtype=GRB.BINARY, name="s")
u = model.addVars(range(len(N)), range(len(K)), range(len(T)), vtype=GRB.INTEGER, name="u")
u_ = model.addVars(range(len(N)), range(len(K)), range(len(T)), vtype=GRB.INTEGER, name="u_")
y = model.addVars(range(len(N)), range(len(P)), range(len(T)), vtype=GRB.BINARY, name="y")
a = model.addVars(range(len(N)), range(len(P)), range(len(T)), vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="a")
v = model.addVars(range(len(N)), range(len(T)), vtype=GRB.CONTINUOUS, lb=0.0, name="v")
z = model.addVars(range(len(P)), range(len(T)), vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z")
o = model.addVars(range(len(N)), range(len(T)), vtype=GRB.BINARY, name="o")
model.update()

# Restricciones
