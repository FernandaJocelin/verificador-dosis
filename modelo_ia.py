import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import os

MEDICAMENTOS_SIMULADOS = [
    "Ceftriaxona", "Amikacina", "Gentamicina", "Ampicilina",
    "Paracetamol", "Ibuprofeno", "Midazolam", "Hidroxizina"
]

DOSIS_REFERENCIA = {
    "Ceftriaxona": 50, "Amikacina": 15, "Gentamicina": 2.5,
    "Ampicilina": 50, "Paracetamol": 15, "Ibuprofeno": 10,
    "Midazolam": 0.1, "Hidroxizina": 0.5
}

VIAS_SIMULADAS = ["IV", "Oral", "IM"]


def generar_datos_simulados(n=500):
    np.random.seed(42)
    datos = []

    for _ in range(n):
        edad = np.random.randint(0, 17)
        peso = round(np.random.uniform(3, 70), 1)
        medicamento = np.random.choice(MEDICAMENTOS_SIMULADOS)
        via = np.random.choice(VIAS_SIMULADAS)
        dosis_mgkg = DOSIS_REFERENCIA[medicamento]
        dosis_esperada = peso * dosis_mgkg

        escenario = np.random.choice(
            ["seguro", "advertencia", "riesgo"], p=[0.6, 0.25, 0.15]
        )

        if escenario == "seguro":
            factor = np.random.uniform(0.90, 1.10)
            clasificacion = 0
        elif escenario == "advertencia":
            factor = np.random.choice([
                np.random.uniform(0.80, 0.90),
                np.random.uniform(1.10, 1.20)
            ])
            clasificacion = 1
        else:
            factor = np.random.choice([
                np.random.uniform(0.50, 0.80),
                np.random.uniform(1.20, 2.00)
            ])
            clasificacion = 2

        dosis_preparada = round(dosis_esperada * factor, 2)
        desviacion = abs(dosis_preparada - dosis_esperada) / dosis_esperada * 100

        datos.append({
            "edad": edad,
            "peso": peso,
            "dosis_mgkg": dosis_mgkg,
            "dosis_esperada": round(dosis_esperada, 2),
            "dosis_preparada": dosis_preparada,
            "desviacion_pct": round(desviacion, 2),
            "medicamento": medicamento,
            "via": via,
            "clasificacion": clasificacion
        })

    return pd.DataFrame(datos)


def entrenar_modelo_simulado():
    df = generar_datos_simulados(500)
    return _entrenar(df)


def entrenar_modelo_real(csv_path):
    if not os.path.exists(csv_path):
        return None, None, None, 0

    df_real = pd.read_csv(csv_path)
    if len(df_real) < 20:
        return None, None, None, len(df_real)

    def clasificar(c):
        if "segura" in c: return 0
        elif "Advertencia" in c: return 1
        else: return 2

    df_real["clasificacion"] = df_real["Clasificacion"].apply(clasificar)
    df_real["desviacion_pct"] = (
        abs(df_real["Dosis_preparada_mg"] - df_real["Dosis_esperada_mg"])
        / df_real["Dosis_esperada_mg"] * 100
    )
    df_real = df_real.rename(columns={
        "Edad": "edad",
        "Peso_kg": "peso",
        "Dosis_esperada_mg": "dosis_esperada",
        "Dosis_preparada_mg": "dosis_preparada"
    })
    df_real["dosis_mgkg"] = df_real["dosis_esperada"] / df_real["peso"]
    df_real["medicamento"] = df_real["Medicamento"]
    df_real["via"] = df_real["Via"].str.extract(r'\((\w+)\)')
    df_real["via"] = df_real["via"].fillna("IV")

    df_real = df_real[[
        "edad", "peso", "dosis_mgkg", "dosis_esperada",
        "dosis_preparada", "desviacion_pct", "medicamento",
        "via", "clasificacion"
    ]]

    modelo, le_med, le_via = _entrenar(df_real)
    return modelo, le_med, le_via, len(df_real)


def _entrenar(df):
    le_med = LabelEncoder()
    le_via = LabelEncoder()
    df["medicamento_enc"] = le_med.fit_transform(df["medicamento"])
    df["via_enc"] = le_via.fit_transform(df["via"])

    features = [
        "edad", "peso", "dosis_mgkg", "dosis_esperada",
        "dosis_preparada", "desviacion_pct", "medicamento_enc", "via_enc"
    ]
    X = df[features]
    y = df["clasificacion"]

    modelo = RandomForestClassifier(n_estimators=100, random_state=42)
    modelo.fit(X, y)

    return modelo, le_med, le_via


def predecir_riesgo(modelo, le_med, le_via, edad, peso, dosis_mgkg,
                    dosis_esperada, dosis_preparada, medicamento, via):
    desviacion = abs(dosis_preparada - dosis_esperada) / dosis_esperada * 100

    medicamento_conocido = medicamento in le_med.classes_
    if medicamento_conocido:
        med_enc = le_med.transform([medicamento])[0]
    else:
        med_enc = 0

    via_corta = via.split("(")[-1].replace(")", "").strip() if "(" in via else via
    if via_corta in le_via.classes_:
        via_enc = le_via.transform([via_corta])[0]
    else:
        via_enc = 0

    X = pd.DataFrame([{
        "edad": edad,
        "peso": peso,
        "dosis_mgkg": dosis_mgkg,
        "dosis_esperada": dosis_esperada,
        "dosis_preparada": dosis_preparada,
        "desviacion_pct": desviacion,
        "medicamento_enc": med_enc,
        "via_enc": via_enc
    }])

    pred = modelo.predict(X)[0]
    proba = modelo.predict_proba(X)[0]
    etiquetas = {0: "Seguro", 1: "Advertencia", 2: "Alto riesgo"}
    confianza = round(max(proba) * 100, 1)

    return etiquetas[pred], confianza, proba, medicamento_conocido