from gurobipy import GRB, Model, quicksum
from model import model

if model.Status == GRB.OPTIMAL:
    print(f"Cobertura de demanda todal óptima: {model.ObjVal}\n")

