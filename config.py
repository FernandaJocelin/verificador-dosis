import json
import os

# Áreas hospitalarias
AREAS_DEFAULT = [
    "Urgencias Pediátricas",
    "Hospitalización Pediátrica",
    "UCI Pediátrica",
    "Quirófano Pediátrico"
]

# Medicamentos base compartidos por todas las áreas
MEDICAMENTOS_BASE = {
    "Ceftriaxona": {
        "dosis_mgkg": {"IV": 50, "IM": 50},
        "dosis_max": 2000,
        "descripcion": "Antibiótico cefalosporina de tercera generación"
    },
    "Amikacina": {
        "dosis_mgkg": {"IV": 15, "IM": 15},
        "dosis_max": 1500,
        "descripcion": "Antibiótico aminoglucósido"
    },
    "Gentamicina": {
        "dosis_mgkg": {"IV": 2.5, "IM": 2.5},
        "dosis_max": 300,
        "descripcion": "Antibiótico aminoglucósido"
    },
    "Ampicilina": {
        "dosis_mgkg": {"IV": 50, "IM": 50, "Oral": 25},
        "dosis_max": 2000,
        "descripcion": "Antibiótico penicilínico"
    },
    "Paracetamol": {
        "dosis_mgkg": {"Oral": 15, "IV": 15},
        "dosis_max": 1000,
        "descripcion": "Analgésico y antipirético"
    },
    "Ibuprofeno": {
        "dosis_mgkg": {"Oral": 10},
        "dosis_max": 400,
        "descripcion": "Antiinflamatorio no esteroideo"
    },
    "Midazolam": {
        "dosis_mgkg": {"IV": 0.1, "IM": 0.2},
        "dosis_max": 10,
        "descripcion": "Benzodiacepina sedante"
    },
    "Hidroxizina": {
        "dosis_mgkg": {"Oral": 0.5, "IM": 0.5},
        "dosis_max": 25,
        "descripcion": "Antihistamínico y ansiolítico"
    }
}

VIAS = ["Intravenosa (IV)", "Oral", "Intramuscular (IM)", "Subcutánea"]
VIAS_CORTAS = {
    "Intravenosa (IV)": "IV",
    "Oral": "Oral",
    "Intramuscular (IM)": "IM",
    "Subcutánea": "SC"
}

MIN_CASOS_ENTRENAMIENTO = 20

# ── Contraseñas ──────────────────────────────────────────────────────────────
def normalizar_nombre(area):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    nombre = area.lower().replace(" ", "_")
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre

def ruta_password(area):
    return f"datos/{normalizar_nombre(area)}_password.json"

def contrasena_default(area):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    pwd = area.lower().replace(" ", "")
    for k, v in reemplazos.items():
        pwd = pwd.replace(k, v)
    return pwd

def cargar_contrasena(area):
    path = ruta_password(area)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("password", contrasena_default(area))
    return contrasena_default(area)

def guardar_contrasena(area, nueva_password):
    path = ruta_password(area)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"password": nueva_password}, f)

def verificar_contrasena(area, password_ingresada):
    return password_ingresada == cargar_contrasena(area)