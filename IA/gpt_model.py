# ============================================================
# Modelo de Optimización Infraestructura de Carga EV (Chile)
# Escala nacional, horizonte 10 años, con V2G + incentivos
# ============================================================

from gurobipy import Model, GRB, quicksum
import math

# -----------------------------
# 0) Parámetros “globales”
# -----------------------------
USDCLP = 900  # tipo de cambio de referencia
T = list(range(1, 11))             # 2025..2034
Tmap = {t: 2024 + t for t in T}    # t=1->2025 ... t=10->2034

# Tipos de cargador K (k)
K = ["AC_22", "DC_50", "DC_150", "DC_150_V2G"]
K_V2G = {"DC_150_V2G"}  # subconjunto V2G

# Potencia nominal (kW) por tipo
P_k = {
    "AC_22": 22,
    "DC_50": 50,
    "DC_150": 150,
    "DC_150_V2G": 150,
}

# Vida útil (años)
L_k = {
    "AC_22": 10,
    "DC_50": 7,
    "DC_150": 7,
    "DC_150_V2G": 7,
}

# Capacidad energética anual por equipo (kWh/año) (derivada con Uavg)
# AC con Uavg=20%, DC con Uavg=15%
CAP_k = {
    "AC_22": 22 * 24 * 0.20 * 365,      # = 38,544
    "DC_50": 50 * 24 * 0.15 * 365,      # = 65,700
    "DC_150": 150 * 24 * 0.15 * 365,    # = 197,100
    "DC_150_V2G": 150 * 24 * 0.15 * 365 # = 197,100
}

# Costos variables de instalación por cargador (CLP/equipo)
C_VAR_k = {
    "AC_22":       4_500_000,
    "DC_50":      75_280_500,
    "DC_150":    105_957_000,
    "DC_150_V2G": 127_148_400,  # ~20% premium por V2G
}

# Mantención variable anual por equipo (5% de CAPEX) (CLP/año por equipo)
M_VAR_k = {k: 0.05 * C_VAR_k[k] for k in K}

# Conjunto de rutas P (corredores nacionales)
P = [
    "Ruta_N1", "Ruta_N2", "Ruta_N3", "Ruta_N4", "Ruta_N5",
    "Ruta_C1", "Ruta_C2", "Ruta_C3", "Ruta_S1", "Ruta_S2",
    "Ruta_AUS"
]

# Nodos candidatos N (33 principales ciudades/puntos)
N = [
 "Arica","Pozo Almonte","Iquique","Tocopilla","Calama","Antofagasta","Taltal","Chañaral","Caldera","Copiapó",
 "Vallenar","La Serena","Coquimbo","Ovalle","Los Vilos","Viña del Mar","Valparaíso","Santiago (Acceso Norte)",
 "Santiago (Acceso Sur)","Rancagua","Curicó","Talca","Linares","Chillán","Concepción","Los Ángeles","Temuco",
 "Valdivia","Osorno","Puerto Montt","Chaitén","Coyhaique","Cochrane"
]

# Mapeo nodos por ruta (A_ip = 1 si i pertenece a p)
ruta_nodos = {
    "Ruta_N1":  ["Arica","Pozo Almonte","Iquique"],
    "Ruta_N2":  ["Iquique","Pozo Almonte","Calama"],
    "Ruta_N3":  ["Calama","Tocopilla","Antofagasta"],
    "Ruta_N4":  ["Antofagasta","Taltal","Chañaral","Caldera","Copiapó"],
    "Ruta_N5":  ["Copiapó","Vallenar","La Serena","Coquimbo","Los Vilos"],
    "Ruta_C1":  ["La Serena","Coquimbo","Ovalle","Los Vilos","Santiago (Acceso Norte)"],
    "Ruta_C2":  ["Santiago (Acceso Sur)","Rancagua","Curicó","Talca"],
    "Ruta_C3":  ["Talca","Concepción"],
    "Ruta_S1":  ["Linares","Chillán","Concepción","Los Ángeles","Temuco"],
    "Ruta_S2":  ["Temuco","Osorno","Puerto Montt"],
    "Ruta_AUS": ["Puerto Montt","Chaitén","Coyhaique","Cochrane"]
}
A_ip = {(i,p): 1 if i in ruta_nodos[p] else 0 for p in P for i in N}

# Política de separación máxima interurbana (km)
R_p = {p: 100.0 for p in P}

# Longitud aproximada por ruta (km) — ajusta si tienes datos precisos
# (Sólo se usa para forzar #mínimo de estaciones en t=T). 
route_km = {
    "Ruta_N1": 308,   # Arica-Iquique aprox
    "Ruta_N2": 386,   # Iquique-Calama aprox
    "Ruta_N3": 215,   # Calama-Antofagasta aprox
    "Ruta_N4": 543,   # Antofagasta-Copiapó (ejemplo del informe)
    "Ruta_N5": 330,   # Copiapó-La Serena aprox
    "Ruta_C1": 471,   # La Serena-Santiago aprox
    "Ruta_C2": 257,   # Santiago-Talca aprox
    "Ruta_C3": 250,   # Talca-Concepción aprox
    "Ruta_S1": 198,   # Chillán-Temuco aprox
    "Ruta_S2": 312,   # Temuco-Puerto Montt aprox
    "Ruta_AUS": 1000  # Austral (tramos largos, conservador)
}
stations_min_required = {p: math.ceil(route_km[p] / R_p[p]) for p in P}

# Capacidad física y de red por nodo (homogéneo)
U_MAX_i  = {i: 10   for i in N}   # máx. cargadores por estación
INST_MAX = { (i,t): 4 for i in N for t in T }  # máx. instalables/año
G_it     = { (i,t): 1500 for i in N for t in T }  # kW de empalme disp.

# Costos fijos
C_FIX_it = {(i,t): 10_000_000 for i in N for t in T}  # abrir/activar estación
M_FIX_it = {(i,t):    500_000 for i in N for t in T}  # mantención fija anual

# V2G – potenciales e incentivos
PHI_BASE_k = {k: (3125 if k in K_V2G else 0) for k in K}   # kWh/año base por equipo V2G
PHI_MAX_k  = {k: (18250 if k in K_V2G else 0) for k in K}  # tope técnico
theta_t    = {t: 1.0 for t in T}           # intensidad política (exógena)
beta_use   = 0.2                            # sensibilidad uso V2G al incentivo
# Efecto simple del incentivo sobre kWh efectivos (puedes refinar si deseas):
PHI_EFF_k_t = { (k,t): (PHI_BASE_k[k]*(1 + beta_use*theta_t[t]) if k in K_V2G else 0)
                for k in K for t in T }
# Beneficio social por kWh V2G y subsidio al usuario (CLP/kWh)
omega_t = {t: 284 for t in T}   # valor social (potencia evitada horas punta)
sigma_t = {t: 150 for t in T}   # subsidio pagado al usuario por V2G (bolsa separada)

# Mínimo V2G por estación activa
m_MIN_it = {(i,t): 1 for i in N for t in T}

# Presupuestos (CLP/año)
B_t = {t: int(30_000_000_000 * (1 + 0.10*(t-1))) for t in T}      # inversión+OPEX
B_INC_t = {t: int(3_000_000_000 * (1 + 0.15*(t-1))) for t in T}   # bolsa subsidios V2G

# Priorización social por ruta (en F.O.)
W_PRIOR_p = {
    "Ruta_C1": 1.0, "Ruta_C2": 1.0,
    "Ruta_C3": 0.9, "Ruta_S1": 0.9, "Ruta_S2": 0.9,
    "Ruta_N1": 0.8, "Ruta_N2": 0.8, "Ruta_N3": 0.8, "Ruta_N4": 0.8, "Ruta_N5": 0.8,
    "Ruta_AUS": 0.7
}

# Curva de penetración EV (fracción de flota/flujo que es EV)
penetracion_EV_t = {
    1:0.005, 2:0.010, 3:0.018, 4:0.030, 5:0.045,
    6:0.065, 7:0.090, 8:0.120, 9:0.155, 10:0.200
}

# AADT por ruta (veh/día) (clústeres nacionales)
AADT_p = {
    "Ruta_N1": 2500, "Ruta_N2": 2500, "Ruta_N3": 2500,    # norte 1
    "Ruta_N4": 3500, "Ruta_N5": 3500,                     # norte 2
    "Ruta_C1": 8000, "Ruta_C2": 15000, "Ruta_C3": 7000,   # centro
    "Ruta_S1": 6000, "Ruta_S2": 5000,                     # sur
    "Ruta_AUS": 800                                      # austral
}

# Tasa de captura (% EV en ruta que cargan)
captura_p = {
    "Ruta_N1":0.40, "Ruta_N2":0.40, "Ruta_N3":0.40, "Ruta_C2":0.40,
    "Ruta_C3":0.40, "Ruta_S1":0.40, "Ruta_S2":0.40,
    "Ruta_N4":0.70, "Ruta_N5":0.70, "Ruta_C1":0.70, "Ruta_AUS":0.80
}
CARGA_MEDIA_kWh = 40.0  # tamaño de recarga por evento (kWh)

# Demanda anual por ruta y año (kWh/año) mediante fórmula estándar
D_pt = {}
for p in P:
    D_pt[p] = {}
    for t in T:
        D_pt[p][t] = AADT_p[p] * 365 * penetracion_EV_t[t] * captura_p[p] * CARGA_MEDIA_kWh

# --------------------------------
# 1) Crear modelo
# --------------------------------
m = Model("EV_Charging_Chile_V2G")

# -----------------------------
# 2) Variables de decisión
# -----------------------------
# s[i,t] = 1 si la estación i está abierta/activa en el año t
s = m.addVars(N, T, vtype=GRB.BINARY, name="s")

# x[i,k,t] = número de cargadores tipo k instalados y operativos en i en t (acumulado)
x = m.addVars(N, K, T, vtype=GRB.INTEGER, lb=0, name="x")

# v[i,t] = número de cargadores V2G en i en t (acumulado)
v = m.addVars(N, T, vtype=GRB.INTEGER, lb=0, name="v")

# z[p,t] ∈ [0,1] = fracción de demanda D_pt atendida en la ruta p en el año t
z = m.addVars(P, T, vtype=GRB.CONTINUOUS, lb=0.0, ub=1.0, name="z")

# --------------------------------
# 3) Restricciones
# --------------------------------

# 3.0) Monotonías (no se desinstala, no se cierra)
for i in N:
    for t in T:
        if t > 1:
            m.addConstr(s[i,t] >= s[i,t-1], name=f"monot_s[{i},{t}]")
            for k in K:
                m.addConstr(x[i,k,t] >= x[i,k,t-1], name=f"monot_x[{i},{k},{t}]")

# 3.1) Capacidad física por estación
for i in N:
    for t in T:
        m.addConstr(quicksum(x[i,k,t] for k in K) <= U_MAX_i[i]*s[i,t],
                    name=f"cap_fisica[{i},{t}]")

# 3.2) Límite anual de instalación
for i in N:
    for t in T:
        if t == 1:
            new_inst = quicksum(x[i,k,t] for k in K)
        else:
            new_inst = quicksum(x[i,k,t] - x[i,k,t-1] for k in K)
        m.addConstr(new_inst <= INST_MAX[(i,t)], name=f"inst_max[{i},{t}]")

# 3.3) Límite de potencia de empalme por nodo
for i in N:
    for t in T:
        m.addConstr(quicksum(P_k[k]*x[i,k,t] for k in K) <= G_it[(i,t)],
                    name=f"empalme[{i},{t}]")

# 3.4) Vínculo V2G: v = sum_{k∈K_V2G} x
for i in N:
    for t in T:
        m.addConstr(v[i,t] == quicksum(x[i,k,t] for k in K if k in K_V2G),
                    name=f"v_link[{i},{t}]")

# 3.5) Mínimo V2G por estación activa
for i in N:
    for t in T:
        m.addConstr(v[i,t] >= m_MIN_it[(i,t)] * s[i,t], name=f"min_v2g[{i},{t}]")

# 3.6) Capacidad para cubrir demanda por ruta (en kWh/año)
# sum_{i∈ruta p} sum_k CAP_k * x[i,k,t] >= D_pt[p,t] * z[p,t]
for p in P:
    for t in T:
        lhs = quicksum(A_ip[(i,p)] * quicksum(CAP_k[k]*x[i,k,t] for k in K) for i in N)
        m.addConstr(lhs >= D_pt[p][t] * z[p,t], name=f"demanda[{p},{t}]")

# 3.7) Cobertura interurbana ≤100 km al final del horizonte:
# Para cada ruta p, exigir al menos ceil(longitud/R_p) estaciones activas en t=T
T_last = T[-1]
for p in P:
    lhs = quicksum(A_ip[(i,p)] * s[i,T_last] for i in N)
    m.addConstr(lhs >= stations_min_required[p], name=f"cobertura100km[{p},{T_last}]")

# 3.8) Presupuesto de inversión + OPEX por año
# cost_t = sum_i (C_FIX*s + M_FIX*s) + sum_{i,k}(C_VAR*x + M_VAR*x)
for t in T:
    inv_opex_t = (
        quicksum(C_FIX_it[(i,t)]*s[i,t] + M_FIX_it[(i,t)]*s[i,t] for i in N) +
        quicksum(C_VAR_k[k]*x[i,k,t] + M_VAR_k[k]*x[i,k,t] for i in N for k in K)
    )
    m.addConstr(inv_opex_t <= B_t[t], name=f"budget_inv_opex[{t}]")

# 3.9) Bolsa de subsidios al usuario V2G por año
# payout_t = sigma_t * sum_{i,k∈K_V2G} phi_eff(k,t) * x[i,k,t]
for t in T:
    payout_t = quicksum((sigma_t[t] * PHI_EFF_k_t[(k,t)] * x[i,k,t]) for i in N for k in K if k in K_V2G)
    m.addConstr(payout_t <= B_INC_t[t], name=f"budget_incentivos[{t}]")

# --------------------------------
# 4) Función Objetivo
# --------------------------------
# Min: (CAPEX + OPEX + Subsidios) - (Beneficio Social V2G) - (Beneficio social por cubrir demanda)
# Par de pesos ajustables para “tirar” la solución:
ALPHA_DEMANDA = 25.0  # CLP por kWh de demanda atendida (ajustable)

total_capex_opex = quicksum(
    C_FIX_it[(i,t)]*s[i,t] + M_FIX_it[(i,t)]*s[i,t] +
    quicksum(C_VAR_k[k]*x[i,k,t] + M_VAR_k[k]*x[i,k,t] for k in K)
    for i in N for t in T
)

total_subsidios = quicksum(
    sigma_t[t] * PHI_EFF_k_t[(k,t)] * x[i,k,t]
    for i in N for k in K if k in K_V2G for t in T
)

beneficio_v2g = quicksum(
    omega_t[t] * PHI_EFF_k_t[(k,t)] * x[i,k,t]
    for i in N for k in K if k in K_V2G for t in T
)

beneficio_demanda = quicksum(
    ALPHA_DEMANDA * W_PRIOR_p[p] * D_pt[p][t] * z[p,t]
    for p in P for t in T
)

# Objetivo: minimizar costo neto
m.setObjective(total_capex_opex + total_subsidios - beneficio_v2g - beneficio_demanda, GRB.MINIMIZE)

# Parámetros del solver (opcional)
m.Params.MIPGap = 0.02
m.Params.TimeLimit = 120  # segundos

# -----------------------------
# 5) Resolver
# -----------------------------
m.optimize()

# -----------------------------
# 6) Reporte mínimo de salida
# -----------------------------
def print_solution():
    if m.SolCount == 0:
        print("No hay solución.")
        return
    print("\n=== Valor Óptimo (CLP) ===")
    print(round(m.ObjVal))

    # Estaciones abiertas en t=T
    abiertos_T = [i for i in N if s[i,T_last].X > 0.5]
    print(f"\nEstaciones abiertas a {Tmap[T_last]} ({len(abiertos_T)}):")
    print(", ".join(abiertos_T))

    # Cargadores por tipo en t=T
    print("\nCargadores por tipo (t=T):")
    for k in K:
        total_k = sum(int(round(x[i,k,T_last].X)) for i in N)
        print(f"  {k:12s}: {total_k}")

    # V2G total y kWh V2G/año
    v2g_total_T = sum(int(round(v[i,T_last].X)) for i in N)
    kWh_v2g_T = sum(PHI_EFF_k_t[(k,T_last)]*x[i,k,T_last].X for i in N for k in K if k in K_V2G)
    print(f"\nV2G total (t=T): {v2g_total_T} equipos")
    print(f"kWh V2G/año (t=T): {int(round(kWh_v2g_T))}")

    # Cobertura de demanda por ruta
    print("\nFracción de demanda atendida z[p,t] en t=T:")
    for p in P:
        print(f"  {p:10s}: {z[p,T_last].X:.2%}")

print_solution()