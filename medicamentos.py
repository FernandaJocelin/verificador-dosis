import json
import os
from config import MEDICAMENTOS_BASE

def cargar_medicamentos(area):
    path = ruta_medicamentos(area)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            extras = json.load(f)
        return {**MEDICAMENTOS_BASE, **extras}
    return dict(MEDICAMENTOS_BASE)

def ruta_medicamentos(area):
    nombre = normalizar_nombre(area)
    return f"datos/{nombre}_medicamentos.json"

def normalizar_nombre(area):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    nombre = area.lower().replace(" ", "_")
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre

def guardar_medicamento_nuevo(area, nombre, dosis_mgkg_dict, dosis_max, descripcion):
    path = ruta_medicamentos(area)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            extras = json.load(f)
    else:
        extras = {}
    extras[nombre] = {
        "dosis_mgkg": dosis_mgkg_dict,
        "dosis_max": dosis_max,
        "descripcion": descripcion
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(extras, f, ensure_ascii=False, indent=2)

def eliminar_medicamento(area, nombre):
    path = ruta_medicamentos(area)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            extras = json.load(f)
        if nombre in extras:
            del extras[nombre]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(extras, f, ensure_ascii=False, indent=2)

def lista_medicamentos_con_alta(area):
    meds = cargar_medicamentos(area)
    opciones = list(meds.keys())
    opciones.append("+ Dar de alta medicamento nuevo")
    return opciones