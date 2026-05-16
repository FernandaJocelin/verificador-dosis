import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from config import (
    AREAS_DEFAULT, MEDICAMENTOS_BASE, VIAS, VIAS_CORTAS,
    MIN_CASOS_ENTRENAMIENTO, normalizar_nombre,
    cargar_contrasena, guardar_contrasena, verificar_contrasena
)
from medicamentos import (
    cargar_medicamentos, guardar_medicamento_nuevo,
    eliminar_medicamento, lista_medicamentos_con_alta,
    ruta_medicamentos
)
from modelo_ia import (
    entrenar_modelo_simulado, entrenar_modelo_real, predecir_riesgo
)
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Verificador de Dosis Segura",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS GLOBAL ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 19px !important; }
p, div, span, li, td, th { font-size: 1.05rem !important; line-height: 1.7 !important; }
h1, [data-testid="stHeading"] h1 { font-size: 5.5rem !important; font-weight: 800 !important; color: #1a237e !important; line-height: 1.1 !important; margin-bottom: 0.4rem !important; letter-spacing: -1px !important; }
h2, [data-testid="stHeading"] h2 { font-size: 3.2rem !important; font-weight: 700 !important; color: #1a237e !important; margin-top: 1.8rem !important; margin-bottom: 0.7rem !important; border-bottom: 3px solid #c5cae9 !important; padding-bottom: 0.4rem !important; letter-spacing: -0.5px !important; }
h3, [data-testid="stHeading"] h3, [data-testid="stHeadingWithActionElements"] h3, div[class*="stHeadingContainer"] h3 { font-size: 2.4rem !important; font-weight: 700 !important; color: #1a237e !important; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; line-height: 1.2 !important; }
h4, [data-testid="stHeading"] h4, div[class*="stHeadingContainer"] h4 { font-size: 2rem !important; font-weight: 700 !important; color: #283593 !important; margin-top: 1.3rem !important; margin-bottom: 0.4rem !important; }
.stTextInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label, .stTextArea label, .stCheckbox label, .stRadio label { font-size: 1.05rem !important; font-weight: 600 !important; color: #1a1a2e !important; margin-bottom: 5px !important; }
.stTextInput input, .stNumberInput input { font-size: 1.05rem !important; padding: 12px 14px !important; min-height: 48px !important; }
.stSelectbox div[data-baseweb="select"] { font-size: 1.05rem !important; min-height: 48px !important; }
.stButton > button { font-size: 1.1rem !important; font-weight: 700 !important; padding: 12px 24px !important; min-height: 50px !important; border-radius: 7px !important; }
.stTabs [data-baseweb="tab-list"] { gap: 0px !important; width: 100% !important; display: flex !important; }
.stTabs [data-baseweb="tab"] { flex: 1 !important; text-align: center !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 16px 8px !important; background-color: #e8eaf6 !important; border: 1px solid #c5cae9 !important; border-bottom: none !important; border-radius: 7px 7px 0 0 !important; color: #444 !important; white-space: nowrap !important; }
.stTabs [aria-selected="true"] { background-color: #ffffff !important; color: #1a237e !important; border-bottom: 3px solid #1a237e !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.8rem !important; }
[data-testid="metric-container"] label { font-size: 1rem !important; font-weight: 600 !important; color: #555 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800 !important; color: #1a237e !important; }
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 1rem !important; }
.streamlit-expanderHeader, details summary { font-size: 1.05rem !important; font-weight: 600 !important; }
.stCaption, small, [data-testid="stCaptionContainer"] { font-size: 0.95rem !important; color: #555 !important; }
.stAlert p, .stAlert div { font-size: 1.05rem !important; line-height: 1.6 !important; }
.stDataFrame, .stDataFrame td, .stDataFrame th { font-size: 1rem !important; }
.stProgress > div > div { height: 12px !important; border-radius: 6px !important; }
hr { border-color: #c5cae9 !important; margin: 1.8rem 0 !important; }
.header-banner { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 1.4rem 2.2rem; border-radius: 12px; margin-bottom: 1.5rem; }
.header-banner h1 { font-size: 2.8rem !important; font-weight: 800 !important; color: white !important; margin: 0 !important; padding: 0 !important; border-bottom: none !important; letter-spacing: -0.5px !important; }
.header-banner p { font-size: 1.15rem !important; color: #c5cae9 !important; margin: 6px 0 0 0 !important; }
div[data-testid="column"] .stButton > button[kind="primary"] { background-color: #1a237e !important; color: white !important; border: none !important; }
div[data-testid="column"] .stButton > button[kind="secondary"] { background-color: #ffffff !important; color: #1a237e !important; border: 2px solid #1a237e !important; }
.stDownloadButton > button { font-size: 1.1rem !important; font-weight: 700 !important; padding: 12px 24px !important; min-height: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
NOMBRE_HOJA = "verificador-dosis-datos"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_sheets():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        hoja = cliente.open(NOMBRE_HOJA).sheet1
        return hoja
    except Exception as e:
        return None

def cargar_historial_sheets(area):
    hoja = conectar_sheets()
    columnas = [
        "Fecha", "Hora", "No_Expediente", "Edad", "Peso_kg", "Diagnostico",
        "Medicamento", "Via", "Dosis_prescrita_mg",
        "Dosis_esperada_mg", "Dosis_preparada_mg",
        "Clasificacion", "Clasificacion_IA", "Confianza_IA", "Alerta", "Area"
    ]
    if hoja is None:
        return pd.DataFrame(columns=columnas)
    try:
        datos = hoja.get_all_records()
        if not datos:
            return pd.DataFrame(columns=columnas)
        df = pd.DataFrame(datos)
        for col in columnas:
            if col not in df.columns:
                df[col] = ""
        df = df[columnas]
        if "Area" in df.columns:
            df = df[df["Area"].astype(str).str.strip() == area.strip()]
        return df
    except Exception as e:
        st.error(f"Error leyendo Sheets: {e}")
        return pd.DataFrame(columns=columnas)

def guardar_caso_sheets(area, datos):
    hoja = conectar_sheets()
    if hoja is None:
        st.warning("No se pudo conectar a Google Sheets. Guardando localmente.")
        guardar_caso_local(area, datos)
        return
    try:
        # Si la hoja está vacía, agregar encabezados
        if not hoja.get_all_values():
            encabezados = [
                "Fecha", "Hora", "No_Expediente", "Edad", "Peso_kg", "Diagnostico",
                "Medicamento", "Via", "Dosis_prescrita_mg",
                "Dosis_esperada_mg", "Dosis_preparada_mg",
                "Clasificacion", "Clasificacion_IA", "Confianza_IA", "Alerta", "Area"
            ]
            hoja.append_row(encabezados)
        datos["Area"] = area
        fila = [str(datos.get(col, "")) for col in [
            "Fecha", "Hora", "No_Expediente", "Edad", "Peso_kg", "Diagnostico",
            "Medicamento", "Via", "Dosis_prescrita_mg",
            "Dosis_esperada_mg", "Dosis_preparada_mg",
            "Clasificacion", "Clasificacion_IA", "Confianza_IA", "Alerta", "Area"
        ]]
        hoja.append_row(fila)
    except Exception as e:
        st.warning(f"Error al guardar en Sheets: {e}. Guardando localmente.")
        guardar_caso_local(area, datos)

# ── Rutas y funciones locales (fallback) ──────────────────────────────────────
def ruta_csv(area):
    return f"datos/{normalizar_nombre(area)}_historial.csv"

def ruta_config(area):
    return f"datos/{normalizar_nombre(area)}_config.json"

def cargar_config_area(area):
    path = ruta_config(area)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"modo_ia": "simulado"}

def guardar_config_area(area, config):
    path = ruta_config(area)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def cargar_historial_local(area):
    path = ruta_csv(area)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=[
        "Fecha", "Hora", "No_Expediente", "Edad", "Peso_kg", "Diagnostico",
        "Medicamento", "Via", "Dosis_prescrita_mg",
        "Dosis_esperada_mg", "Dosis_preparada_mg",
        "Clasificacion", "Clasificacion_IA", "Confianza_IA", "Alerta"
    ])

def guardar_caso_local(area, datos):
    path = ruta_csv(area)
    df = cargar_historial_local(area)
    nuevo = pd.DataFrame([datos])
    df = pd.concat([df, nuevo], ignore_index=True)
    df.to_csv(path, index=False)

# ── Función principal de historial (local) ───────────────────────────────────
def cargar_historial(area):
    return cargar_historial_local(area)

def guardar_caso(area, datos):
    guardar_caso_local(area, datos)

# ── Validación clínica ────────────────────────────────────────────────────────
def validar_dosis(peso, dosis_mgkg, concentracion, volumen, dosis_max=None):
    dosis_esperada = peso * dosis_mgkg
    dosis_preparada = concentracion * volumen
    advertencias_extra = []

    if dosis_max and dosis_esperada > dosis_max:
        advertencias_extra.append(
            f"La dosis esperada ({dosis_esperada:.1f} mg) supera el máximo recomendado "
            f"({dosis_max} mg). Se aplicará la dosis máxima como referencia."
        )
        dosis_esperada = dosis_max

    limite_inf = dosis_esperada * 0.90
    limite_sup = dosis_esperada * 1.10

    if limite_inf <= dosis_preparada <= limite_sup:
        clasificacion = "Dosis segura"
        alerta = "La dosis preparada está dentro del rango esperado."
        color = "success"
    elif dosis_esperada * 0.80 <= dosis_preparada <= dosis_esperada * 1.20:
        clasificacion = "Advertencia"
        alerta = "La dosis se desvía entre 10% y 20% del valor esperado. Revisar cálculo y preparación."
        color = "warning"
    else:
        pct = abs(dosis_preparada - dosis_esperada) / dosis_esperada * 100
        clasificacion = "Alto riesgo"
        alerta = f"La dosis se desvía un {pct:.1f}% del valor esperado. No administrar hasta verificar."
        color = "error"

    return dosis_esperada, dosis_preparada, clasificacion, alerta, color, advertencias_extra

# ── Modelo IA ─────────────────────────────────────────────────────────────────
@st.cache_resource
def modelo_simulado_cache():
    return entrenar_modelo_simulado()

def obtener_modelo(area, modo):
    if modo == "simulado":
        m, le_m, le_v = modelo_simulado_cache()
        return m, le_m, le_v, None
    else:
        m, le_m, le_v, n = entrenar_modelo_real(ruta_csv(area))
        return m, le_m, le_v, n

# ── LOGIN ─────────────────────────────────────────────────────────────────────
if "area_activa" not in st.session_state:
    st.session_state.area_activa = None

if st.session_state.area_activa is None:
    st.markdown("""
    <style>
    .login-header { text-align: center; padding: 2rem 0 1rem 0; }
    .login-header h1 { font-size: 4.2rem !important; font-weight: 800 !important; color: #1a237e !important; margin-bottom: 0.4rem !important; line-height: 1.1 !important; letter-spacing: -1px !important; }
    .login-header p { font-size: 1.3rem !important; color: #5c6bc0 !important; margin: 0 !important; }
    .login-card h2 { font-size: 2.5rem !important; font-weight: 700 !important; color: #1a237e !important; margin-bottom: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col_centro, _ = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("""
        <div class="login-header">
            <h1>Sistema de Verificación de Dosis Segura</h1>
            <p> Proyecto ULSA México &amp; CUE Alexander von Humboldt Colombia </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-card"><h2>Inicio de sesión</h2></div>', unsafe_allow_html=True)
        area_sel = st.selectbox("Área hospitalaria", AREAS_DEFAULT)
        password = st.text_input("Contraseña", type="password")

        if st.button("Ingresar", type="primary", use_container_width=True):
            if verificar_contrasena(area_sel, password):
                st.session_state.area_activa = area_sel
                st.rerun()
            else:
                st.error("Contraseña incorrecta. Intenta de nuevo.")

        st.caption("Contraseña por defecto: nombre del área en minúsculas sin espacios ni acentos. Ejemplo: urgenciaspediatricas")
        st.divider()
        st.info("Este sistema es una herramienta de apoyo clínico para la verificación de dosis de medicamentos pediátricos. No reemplaza el criterio del personal de salud ni la indicación del médico tratante.")
        st.divider()
        st.subheader("Guía de uso del sistema")

        with st.expander("¿Para qué sirve este sistema?"):
            st.markdown("El Sistema de Verificación de Dosis Segura es una herramienta de apoyo clínico diseñada para el personal de enfermería. Su función principal es **verificar si la dosis de un medicamento pediátrico es segura antes de administrarla**, comparando la dosis preparada con el rango esperado según el peso del paciente.")

        with st.expander("¿Cómo inicio sesión?"):
            st.markdown("Selecciona el **área hospitalaria** donde te encuentras trabajando e ingresa la **contraseña** asignada. La contraseña por defecto es el nombre del área en minúsculas, sin espacios ni acentos. Por ejemplo: **urgenciaspediatricas**")

        with st.expander("¿Cómo verifico una dosis?"):
            st.markdown("En la pestaña **Verificar dosis** ingresa los datos del paciente, del medicamento y de preparación. Luego presiona **Verificar dosis**.")

        with st.expander("¿Cómo interpreto el resultado?"):
            st.markdown("**Dosis segura** — desviación menor al 10%. **Advertencia** — desviación entre 10% y 20%. **Alto riesgo** — desviación mayor al 20%.")

        with st.expander("Aviso importante"):
            st.warning("Este sistema es una herramienta de apoyo a la decisión clínica. No reemplaza el criterio del personal de salud ni la indicación del médico tratante.")

    st.stop()

# ── APP PRINCIPAL ─────────────────────────────────────────────────────────────
area = st.session_state.area_activa
config_area = cargar_config_area(area)
medicamentos = cargar_medicamentos(area)

col_titulo, col_cerrar = st.columns([5, 1])
with col_titulo:
    st.markdown(f"""
    <div class="header-banner">
        <h1>Sistema de Verificación de Dosis Segura</h1>
        <p>COIL · ULSA México &amp; CUE Alexander von Humboldt, Colombia &nbsp;|&nbsp; <strong style="color:white">Área: {area}</strong></p>
    </div>
    """, unsafe_allow_html=True)
with col_cerrar:
    st.write("")
    st.write("")
    st.write("")
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.area_activa = None
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍  Verificar dosis",
    "💊  Medicamentos",
    "📊  Retroalimentación",
    "📋  Historial",
    "⚙️  Configuración"
])

# ── TAB 1: VERIFICAR DOSIS ────────────────────────────────────────────────────
with tab1:
    modo_ia = config_area.get("modo_ia", "simulado")
    df_hist = cargar_historial(area)
    n_casos = len(df_hist)

    st.subheader("Modo de Inteligencia Artificial")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("Modo ya entrenado — datos simulados", use_container_width=True, type="primary" if modo_ia == "simulado" else "secondary"):
            config_area["modo_ia"] = "simulado"
            guardar_config_area(area, config_area)
            st.rerun()
    with col_m2:
        if st.button(f"Modo nuevo — {n_casos} casos reales registrados", use_container_width=True, type="primary" if modo_ia == "real" else "secondary"):
            config_area["modo_ia"] = "real"
            guardar_config_area(area, config_area)
            st.rerun()

    if modo_ia == "simulado":
        st.info("Modelo activo: entrenado con 500 casos simulados.")
    else:
        if n_casos < MIN_CASOS_ENTRENAMIENTO:
            st.warning(f"Modo nuevo activo — {n_casos} de {MIN_CASOS_ENTRENAMIENTO} casos reales requeridos.")
        else:
            st.success(f"Modo nuevo activo — modelo entrenado con {n_casos} casos reales.")

    st.divider()
    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        st.subheader("Datos del paciente")
        no_expediente = st.text_input("No. de expediente")
        edad = st.number_input("Edad (años)", min_value=0, max_value=17, step=1)
        peso = st.number_input("Peso (kg)", min_value=0.1, max_value=150.0, step=0.1, format="%.1f")
        diagnostico = st.text_input("Diagnóstico clínico")

        st.subheader("Medicamento")
        opciones_med = list(medicamentos.keys())
        medicamento_sel = st.selectbox("Selecciona el medicamento", opciones_med)
        info_med = medicamentos[medicamento_sel]
        if info_med["descripcion"]:
            st.caption(f"ℹ️ {info_med['descripcion']}")
        st.caption("Si el medicamento requerido no aparece en la lista, regístrelo en la pestaña Medicamentos.")
        via_sel = st.selectbox("Vía de administración", VIAS)

    with col_der:
        st.subheader("Dosis y preparación")
        via_corta = VIAS_CORTAS.get(via_sel, "IV")
        dosis_sugerida = info_med["dosis_mgkg"].get(via_corta, 0.0)
        if dosis_sugerida > 0:
            st.info(f"Dosis recomendada para **{medicamento_sel}** vía {via_corta}: **{dosis_sugerida} mg/kg**")
        dosis_mgkg = st.number_input("Dosis recomendada (mg/kg)", min_value=0.0, value=float(dosis_sugerida), step=0.1, format="%.2f")
        dosis_prescrita = st.number_input("Dosis prescrita (mg)", min_value=0.0, step=0.1, format="%.2f")
        st.subheader("Preparación")
        concentracion = st.number_input("Concentración disponible (mg/mL)", min_value=0.0, step=0.1, format="%.2f")
        volumen = st.number_input("Volumen preparado (mL)", min_value=0.0, step=0.1, format="%.2f")
        if concentracion > 0 and volumen > 0:
            st.info(f"Dosis calculada de la preparación: **{concentracion * volumen:.2f} mg**")

    st.divider()

    if st.button("✅  Verificar dosis", use_container_width=True, type="primary"):
        if not no_expediente:
            st.error("Ingresa el número de expediente del paciente.")
        elif peso == 0 or dosis_mgkg == 0 or concentracion == 0 or volumen == 0:
            st.error("Completa todos los campos antes de verificar.")
        else:
            dosis_esperada, dosis_preparada, clasificacion, alerta, color, advertencias = validar_dosis(
                peso, dosis_mgkg, concentracion, volumen, info_med["dosis_max"]
            )
            for adv in advertencias:
                st.warning(adv)

            st.subheader("Resultado de la validación")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Dosis esperada", f"{dosis_esperada:.2f} mg")
            with c2:
                st.metric("Dosis preparada", f"{dosis_preparada:.2f} mg", delta=f"{dosis_preparada - dosis_esperada:+.2f} mg")
            with c3:
                desviacion = abs(dosis_preparada - dosis_esperada) / dosis_esperada * 100
                st.metric("Desviación", f"{desviacion:.1f}%")

            st.write("")
            if color == "success":
                st.success(f"**{clasificacion}** — {alerta}")
            elif color == "warning":
                st.warning(f"**{clasificacion}** — {alerta}")
            else:
                st.error(f"**{clasificacion}** — {alerta}")

            modelo, le_med, le_via, n_reales = obtener_modelo(area, modo_ia)
            clasificacion_ia = "No disponible"
            confianza_ia = 0

            if modelo:
                pred_ia, confianza_ia, _, med_conocido = predecir_riesgo(
                    modelo, le_med, le_via, edad, peso, dosis_mgkg,
                    dosis_esperada, dosis_preparada, medicamento_sel, via_sel
                )
                clasificacion_ia = pred_ia
                st.subheader("Clasificación por Inteligencia Artificial")
                col_ia1, col_ia2 = st.columns(2)
                with col_ia1:
                    st.metric("Clasificación IA", clasificacion_ia)
                with col_ia2:
                    st.metric("Confianza del modelo", f"{confianza_ia}%")
                st.progress(int(confianza_ia))
                if not med_conocido:
                    st.warning("El medicamento seleccionado no forma parte del conjunto de entrenamiento del modelo simulado. La clasificación puede no ser precisa.")
            else:
                st.info(f"La clasificación por IA estará disponible cuando se registren al menos {MIN_CASOS_ENTRENAMIENTO} casos reales. Casos actuales: {n_reales}.")

            ahora = datetime.now()
            guardar_caso(area, {
                "Fecha": ahora.strftime("%Y-%m-%d"),
                "Hora": ahora.strftime("%H:%M:%S"),
                "No_Expediente": no_expediente,
                "Edad": edad,
                "Peso_kg": peso,
                "Diagnostico": diagnostico,
                "Medicamento": medicamento_sel,
                "Via": via_sel,
                "Dosis_prescrita_mg": dosis_prescrita,
                "Dosis_esperada_mg": round(dosis_esperada, 2),
                "Dosis_preparada_mg": round(dosis_preparada, 2),
                "Clasificacion": clasificacion,
                "Clasificacion_IA": clasificacion_ia,
                "Confianza_IA": confianza_ia,
                "Alerta": alerta
            })
            st.caption(f"Caso registrado el {ahora.strftime('%d/%m/%Y')} a las {ahora.strftime('%H:%M')} | Expediente: {no_expediente}")

# ── TAB 2: MEDICAMENTOS ───────────────────────────────────────────────────────
with tab2:
    st.subheader("Gestión de medicamentos")
    st.caption("Los medicamentos registrados aquí estarán disponibles únicamente para esta área.")

    path_med = ruta_medicamentos(area)
    extras = {}
    if os.path.exists(path_med):
        with open(path_med, "r", encoding="utf-8") as f:
            extras = json.load(f)

    st.markdown("#### Medicamentos registrados en esta área")
    if extras:
        for nom, dat in extras.items():
            with st.expander(f"💊  {nom} — {dat.get('descripcion', '')}"):
                with st.form(f"edit_{nom}"):
                    nueva_desc = st.text_input("Descripción", value=dat.get("descripcion", ""))
                    nuevo_max = st.number_input("Dosis máxima (mg)", min_value=0.0, value=float(dat.get("dosis_max") or 0), step=1.0)
                    st.markdown("**Dosis por vía (mg/kg)** — deja en 0 si no aplica")
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        e_iv = st.number_input("Intravenosa (IV)", min_value=0.0, value=float(dat["dosis_mgkg"].get("IV", 0)), step=0.1, format="%.2f", key=f"iv_{nom}")
                    with col_e2:
                        e_oral = st.number_input("Oral", min_value=0.0, value=float(dat["dosis_mgkg"].get("Oral", 0)), step=0.1, format="%.2f", key=f"oral_{nom}")
                    with col_e3:
                        e_im = st.number_input("Intramuscular (IM)", min_value=0.0, value=float(dat["dosis_mgkg"].get("IM", 0)), step=0.1, format="%.2f", key=f"im_{nom}")

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        guardar = st.form_submit_button("Guardar cambios", type="primary", use_container_width=True)
                    with col_btn2:
                        eliminar = st.form_submit_button("Eliminar medicamento", use_container_width=True)

                    if guardar:
                        dosis_dict = {}
                        if e_iv > 0: dosis_dict["IV"] = e_iv
                        if e_oral > 0: dosis_dict["Oral"] = e_oral
                        if e_im > 0: dosis_dict["IM"] = e_im
                        guardar_medicamento_nuevo(area, nom, dosis_dict, nuevo_max if nuevo_max > 0 else None, nueva_desc)
                        st.success(f"Medicamento '{nom}' actualizado correctamente.")
                        st.rerun()
                    if eliminar:
                        eliminar_medicamento(area, nom)
                        st.success(f"Medicamento '{nom}' eliminado.")
                        st.rerun()
    else:
        st.info("No hay medicamentos adicionales registrados en esta área.")

    st.divider()
    st.markdown("#### Registrar nuevo medicamento")
    with st.form("form_nuevo_med"):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            nombre = st.text_input("Nombre del medicamento")
        with col_n2:
            descripcion = st.text_input("Descripción breve")
        dosis_max = st.number_input("Dosis máxima (mg)", min_value=0.0, step=1.0)
        st.markdown("**Dosis recomendada por vía (mg/kg)** — deja en 0 si no aplica")
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            d_iv = st.number_input("Intravenosa (IV)", min_value=0.0, step=0.1, format="%.2f")
        with col_v2:
            d_oral = st.number_input("Oral", min_value=0.0, step=0.1, format="%.2f")
        with col_v3:
            d_im = st.number_input("Intramuscular (IM)", min_value=0.0, step=0.1, format="%.2f")
        submitted = st.form_submit_button("Registrar medicamento", type="primary", use_container_width=True)
        if submitted:
            if not nombre:
                st.error("Ingresa el nombre del medicamento.")
            else:
                dosis_dict = {}
                if d_iv > 0: dosis_dict["IV"] = d_iv
                if d_oral > 0: dosis_dict["Oral"] = d_oral
                if d_im > 0: dosis_dict["IM"] = d_im
                if not dosis_dict:
                    st.error("Ingresa al menos una dosis por vía de administración.")
                else:
                    guardar_medicamento_nuevo(area, nombre, dosis_dict, dosis_max if dosis_max > 0 else None, descripcion)
                    st.success(f"Medicamento '{nombre}' registrado correctamente.")
                    st.rerun()

# ── TAB 3: RETROALIMENTACIÓN ──────────────────────────────────────────────────
with tab3:
    st.subheader(f"Retroalimentación — {area}")
    df = cargar_historial(area)
    if df.empty:
        st.info("Aún no hay casos registrados en esta área.")
    else:
        total = len(df)
        seguros = len(df[df["Clasificacion"].astype(str).str.contains("segura")])
        advertencias_t = len(df[df["Clasificacion"].astype(str).str.contains("Advertencia")])
        riesgos = len(df[df["Clasificacion"].astype(str).str.contains("riesgo")])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de casos validados", total)
        c2.metric("✅  Dosis segura", seguros)
        c3.metric("⚠️  Advertencia", advertencias_t)
        c4.metric("🚨  Alto riesgo", riesgos)

        st.divider()
        st.markdown("**Medicamentos con mayor frecuencia de alertas**")
        df_alertas = df[df["Clasificacion"].astype(str).str.contains("Advertencia|riesgo")]
        if not df_alertas.empty:
            conteo = df_alertas["Medicamento"].value_counts().reset_index()
            conteo.columns = ["Medicamento", "Alertas"]
            st.bar_chart(conteo.set_index("Medicamento"))
        else:
            st.success("No se han registrado alertas en esta área.")

        st.divider()
        st.markdown("**Resumen de alertas por medicamento**")
        resumen = df.groupby("Medicamento")["Clasificacion"].apply(
            lambda x: (x.astype(str).str.contains("Advertencia|riesgo")).sum()
        ).reset_index()
        resumen.columns = ["Medicamento", "Casos con alerta"]
        resumen = resumen[resumen["Casos con alerta"] > 0].sort_values("Casos con alerta", ascending=False)
        if resumen.empty:
            st.success("No se han detectado errores frecuentes.")
        else:
            st.dataframe(resumen, use_container_width=True)

# ── TAB 4: HISTORIAL ──────────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Historial de casos — {area}")
    df = cargar_historial(area)

    if df.empty:
        st.info("Aún no hay casos registrados en esta área.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_exp = st.text_input("Buscar por No. de expediente")
        with col_f2:
            filtro_med = st.multiselect("Filtrar por medicamento", df["Medicamento"].unique())
        with col_f3:
            filtro_clas = st.multiselect("Filtrar por clasificación", df["Clasificacion"].unique())

        df_filtrado = df.copy()
        if filtro_exp:
            df_filtrado = df_filtrado[df_filtrado["No_Expediente"].astype(str).str.contains(filtro_exp)]
        if filtro_med:
            df_filtrado = df_filtrado[df_filtrado["Medicamento"].isin(filtro_med)]
        if filtro_clas:
            df_filtrado = df_filtrado[df_filtrado["Clasificacion"].isin(filtro_clas)]

        st.dataframe(df_filtrado, use_container_width=True, height=450)
        csv = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Descargar historial en CSV",
            data=csv,
            file_name=f"historial_{normalizar_nombre(area)}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ── TAB 5: CONFIGURACIÓN ──────────────────────────────────────────────────────
with tab5:
    st.subheader(f"Configuración — {area}")
    st.divider()

    st.markdown("#### Cambiar contraseña")
    with st.form("form_password"):
        pwd_actual = st.text_input("Contraseña actual", type="password")
        pwd_nueva = st.text_input("Nueva contraseña", type="password")
        pwd_confirmar = st.text_input("Confirmar nueva contraseña", type="password")
        submitted_pwd = st.form_submit_button("Actualizar contraseña", type="primary", use_container_width=True)
        if submitted_pwd:
            if not verificar_contrasena(area, pwd_actual):
                st.error("La contraseña actual es incorrecta.")
            elif pwd_nueva != pwd_confirmar:
                st.error("Las contraseñas nuevas no coinciden.")
            elif len(pwd_nueva) < 6:
                st.error("La nueva contraseña debe tener al menos 6 caracteres.")
            else:
                guardar_contrasena(area, pwd_nueva)
                st.success("Contraseña actualizada correctamente.")

    st.divider()
    st.markdown("#### Modo nuevo — Gestión del aprendizaje real")
    df_hist = cargar_historial(area)
    n_casos = len(df_hist)
    st.info(f"Casos reales registrados en esta área: **{n_casos}**")
    if n_casos >= MIN_CASOS_ENTRENAMIENTO:
        st.success(f"El modelo de aprendizaje real está activo con {n_casos} casos.")
    else:
        st.warning(f"Se requieren al menos {MIN_CASOS_ENTRENAMIENTO} casos para activar el modo nuevo. Casos faltantes: {MIN_CASOS_ENTRENAMIENTO - n_casos}.")

    st.divider()
    st.markdown("#### Reiniciar aprendizaje desde cero")
    st.warning("Esta acción eliminará todo el historial real del área. No se puede deshacer.")
    confirmar = st.checkbox("Confirmo que deseo eliminar el historial de aprendizaje real")
    if confirmar:
        if st.button("Reiniciar aprendizaje", type="primary", use_container_width=True):
            path = ruta_csv(area)
            if os.path.exists(path):
                os.remove(path)
            st.success("Historial eliminado. El modo nuevo comenzará desde cero.")
            st.rerun()