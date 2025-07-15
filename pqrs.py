import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Cm
from num2words import num2words
from io import BytesIO

# Configuración de la app
st.set_page_config(page_title="Generador PQRS Convocatorias", layout="wide")

st.title("📄 Generador de PQRS para Convocatorias de Línea Pregrado")
st.subheader("Sapiencia - Medellín")

# Función para convertir número a texto
def formato_numero(n):
    try:
        n = float(n)
        if n.is_integer():
            n = int(n)
        texto = num2words(n, lang='es')
        return f"{texto} ({n})"
    except (TypeError, ValueError):
        return n

# Cargar base de datos interna
@st.cache_data
def cargar_datos():
    ruta_parquet = "/app/Resultados_Linea_pregrado_2025-2.parquet"
    try:
        df = pd.read_parquet(ruta_parquet)
        df.fillna(0, inplace=True)
        df['Nombre'] = df['Nombre'].astype(str).str.upper()
        df['Documento'] = df['Documento'].astype(str)
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {str(e)}")
        return None

# Generar documento según plantilla y tipo
def generar_documento(tipo_documento, row, radicado, imagen1=None, imagen2=None):
    context = row.to_dict()
    context['radicado'] = radicado  # Agregamos el radicado ingresado

    for key in context:
        if key.startswith('cal'):
            context[key] = formato_numero(context[key])

    template_path = {
        "LEGALIZACIÓN RECHAZADA": "legalizacion_rechazada.docx",
        "NO PRESELECCIONADO POR PUNTO DE CORTE PP": "No_preseleccionado_por_punto_corte_pp.docx",
        "NO CUMPLE HABILITANTE ART.70 LITERAL B": "No_cumple_habilitante_b.docx",
    }[tipo_documento]

    doc = DocxTemplate(template_path)

    # Insertar imágenes redimensionadas según plantilla
    if tipo_documento == "NO PRESELECCIONADO POR PUNTO DE CORTE PP":
        context['imagen_1'] = InlineImage(doc, imagen1, height=Cm(4.88)) if imagen1 else ''
        context['imagen_2'] = InlineImage(doc, imagen2, width=Cm(14.91), height=Cm(3.92)) if imagen2 else ''
    elif tipo_documento == "LEGALIZACIÓN RECHAZADA":
        context['imagen_1'] = InlineImage(doc, imagen1, width=Cm(17.51), height=Cm(1.88)) if imagen1 else ''
        context['imagen_2'] = ''
    elif tipo_documento == "NO CUMPLE HABILITANTE ART.70 LITERAL B":
        context['imagen_1'] = InlineImage(doc, imagen1, width=Cm(12.91), height=Cm(12.18)) if imagen1 else ''
        context['imagen_2'] = ''

    doc.render(context)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Cargar datos
df = cargar_datos()

if df is not None:
    st.success(f"Base de datos cargada con {len(df)} registros.")

    doc_busqueda = st.text_input("🔎 Ingrese el número de documento del aspirante:")
    resultado = df[df['Documento'] == doc_busqueda] if doc_busqueda else pd.DataFrame()

    if not resultado.empty:
        row = resultado.iloc[0]
        st.success(f"Aspirante encontrado: {row['Nombre']}")

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
            st.info(f"**Punto de corte PP:** {row['punto_corte_pp']}")
        with col3:
            st.info(f"**Resultado PP:** {row['Observaciones Presupuesto Participativo']}")

        # Campo radicado (antes de seleccionar plantilla)
        radicado = st.text_input("✍️ Ingrese el número de radicado:", max_chars=30)

        # Selección de tipo de documento
        tipo_documento = st.selectbox(
            "📄 Seleccione el tipo de documento a generar:",
            ["LEGALIZACIÓN RECHAZADA", "NO PRESELECCIONADO POR PUNTO DE CORTE PP", "NO CUMPLE HABILITANTE ART.70 LITERAL B"]
        )

        # Subida de imágenes
        if tipo_documento == "NO PRESELECCIONADO POR PUNTO DE CORTE PP":
            st.markdown("📷 Suba las dos imágenes requeridas para el documento:")
            imagen1 = st.file_uploader("Imagen 1 (para {{imagen_1}})", type=["jpg", "jpeg", "png"], key="img1")
            imagen2 = st.file_uploader("Imagen 2 (para {{imagen_2}})", type=["jpg", "jpeg", "png"], key="img2")
        else:
            st.markdown("📷 Suba la imagen requerida para el documento:")
            imagen1 = st.file_uploader("Imagen 1 (para {{imagen_1}})", type=["jpg", "jpeg", "png"], key="img1")
            imagen2 = None

        # Botón para generar
        if st.button("✅ Generar Documento"):
            if not radicado.strip():
                st.warning("Debe ingresar el número de radicado.")
            elif tipo_documento == "NO PRESELECCIONADO POR PUNTO DE CORTE PP" and (imagen1 is None or imagen2 is None):
                st.warning("Debe subir ambas imágenes.")
            elif tipo_documento != "NO PRESELECCIONADO POR PUNTO DE CORTE PP" and imagen1 is None:
                st.warning("Debe subir una imagen.")
            else:
                buffer = generar_documento(tipo_documento, row, radicado, imagen1, imagen2)
                nombre_doc = f"{tipo_documento.replace(' ', '_')}_{row['Documento']}_{row['Nombre'][:20]}.docx"

                st.download_button(
                    label="📥 Descargar Documento",
                    data=buffer,
                    file_name=nombre_doc,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    elif doc_busqueda:
        st.warning("No se encontró ningún aspirante con ese documento.")
