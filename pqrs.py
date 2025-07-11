import streamlit as st
import pandas as pd
import numpy as np
from docxtpl import DocxTemplate
from num2words import num2words
from io import BytesIO
import os

# Configuración inicial
st.set_page_config(page_title="Generador PQRS Convocatorias", layout="wide")

# Título principal
st.title("📄 Generador de PQRS para Convocatorias de Línea Pregrado")
st.subheader("Sapiencia - Medellín")

# Función para formatear números
def formato_numero(n):
    try:
        n = float(n)
        if n.is_integer():
            n = int(n)
        texto = num2words(n, lang='es')
        return f"{texto} ({n})"
    except (TypeError, ValueError):
        return n

# Carga de datos desde archivo Parquet interno
@st.cache_data
def cargar_datos():
    # Ruta interna del archivo Parquet
    ruta_parquet = "/app/Resultados_Linea_pregrado_2025-2.parquet"
   
    try:
        df = pd.read_parquet(ruta_parquet)
        df.fillna(0, inplace=True)
        df['Nombre'] = df['Nombre'].astype(str).str.upper()
        df['Documento'] = df['Documento'].astype(str)  # Asegurar tipo string
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {str(e)}")
        return None

# Procesamiento de documentos
def generar_documento(tipo_documento, row):
    # Preprocesar campos numéricos
    context = row.to_dict()
    for key in context:
        if key.startswith('cal'):
            context[key] = formato_numero(context[key])
   
    # Seleccionar plantilla
    template_path = {
        "LEGALIZACIÓN RECHAZADA": "legalizacion_rechazada.docx",
        "NO PRESELECCIONADO POR PUNTO DE CORTE PP": "No_preseleccionado_por_punto_corte_pp.docx",
        "NO CUMPLE HABILITANTE ART.70 LITERAL B": "No_cumple_habilitante_b.docx",
    }[tipo_documento]
   
    # Generar documento
    doc = DocxTemplate(template_path)
    doc.render(context)
   
    # Preparar archivo para descarga
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
   
    return buffer

# Cargar datos automáticamente
df = cargar_datos()

if df is not None:
    st.success(f"Base de datos cargada internamente con {len(df)} registros")
   
    # Búsqueda por documento
    doc_busqueda = st.text_input("Ingrese el número de documento a buscar:")
    resultado = df[df['Documento'] == doc_busqueda] if doc_busqueda else pd.DataFrame()

    if not resultado.empty:
        row = resultado.iloc[0]
        st.success(f"Aspirante encontrado: {row['Nombre']}")
       
        # Mostrar información básica
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Documento:** {row['Documento']}")
        with col2:
            st.info(f"**Comuna:** {row['Comuna']}")
        with col2:
            st.info(f"**Estrato:** {row['Estrato']}")
        with col3:
            st.info(f"**Puntaje total:** {row['cal_total']}")
        with col3:
            st.info(f"**Puntaje de corte PP:** {row['punto_corte_pp']}")
        with col3:
            st.info(f"**RESULTADO CONVOCATORIA PP:** {row['Observaciones Presupuesto Participativo']}")
       
        # Selección de documento a generar
        tipo_documento = st.selectbox(
            "Seleccione el tipo de documento a generar:",
            ["LEGALIZACIÓN RECHAZADA", "NO PRESELECCIONADO POR PUNTO DE CORTE PP", "NO CUMPLE HABILITANTE ART.70 LITERAL B"]
        )
       
        # Generar documento
        if st.button("Generar Documento"):
            buffer = generar_documento(tipo_documento, row)
            nombre_doc = f"{tipo_documento.replace(' ', '_')}_{row['Documento']}_{row['Nombre'][:20]}.docx"
           
            st.download_button(
                label="Descargar Documento",
                data=buffer,
                file_name=nombre_doc,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    elif doc_busqueda:
        st.warning("No se encontró ningún aspirante con ese documento")
