import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Cm
from num2words import num2words
from io import BytesIO
from sqlalchemy import create_engine, text
import hashlib
import secrets
from typing import Optional

# Configuración de la aplicación
st.set_page_config(page_title="Generador PQRS Convocatorias", layout="wide")

# Configuración de bases de datos (igual que en app.py)
LOGIN_DB_CONFIG = {
    'host': '10.124.80.4', #usa ésta IP para desplegar la aplicacion
    #'host': '34.70.133.119', # usa esta ip cuando estés en una red autorizada
    'user': 'arley',
    'password': 'E*d)HppA}.PcaMtD',
    'database': 'analitica_fondos',
    'port': 3306
}

APP_DB_CONFIG = {
    'host': '10.124.80.4',  #usa ésta IP para desplegar la aplicacion
    #'host': '34.70.133.119', # usa esta ip cuando estés en una red autorizada
    'user': 'arley',
    'password': 'E*d)HppA}.PcaMtDp',
    'database': 'convocatoria_sapiencia',
    'port': 3306
}


# Conexión a la base de datos de login (igual que en app.py)
@st.cache_resource
def init_login_connection():
    try:
        connection_string = f"mysql+mysqlconnector://{LOGIN_DB_CONFIG['user']}:{LOGIN_DB_CONFIG['password']}@{LOGIN_DB_CONFIG['host']}:{LOGIN_DB_CONFIG['port']}/{LOGIN_DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de autenticación: {e}")
        return None


# Conexión a la base de datos de aplicación (igual que en app.py)
@st.cache_resource
def init_app_connection():
    try:
        connection_string = f"mysql+mysqlconnector://{APP_DB_CONFIG['user']}:{APP_DB_CONFIG['password']}@{APP_DB_CONFIG['host']}:{APP_DB_CONFIG['port']}/{APP_DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de aplicación: {e}")
        return None


# Funciones de seguridad mejoradas (igual que en app.py)
def crear_hash_con_sal(password: str) -> tuple:
    """Crea un hash seguro de la contraseña con sal"""
    try:
        sal = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            sal.encode('utf-8'),
            100000
        )
        return sal, hash_obj.hex()
    except Exception as e:
        st.error(f"Error al crear hash: {str(e)}")
        return None, None


def verificar_password(sal: str, hash_almacenado: str, password_proporcionado: str) -> bool:
    """Verifica si el password proporcionado coincide con el hash almacenado"""
    try:
        if not all([sal, hash_almacenado, password_proporcionado]):
            return False

        hash_calculado = hashlib.pbkdf2_hmac(
            'sha256',
            password_proporcionado.encode('utf-8'),
            sal.encode('utf-8'),
            100000
        ).hex()

        return hash_calculado == hash_almacenado
    except Exception as e:
        st.error(f"Error al verificar contraseña: {str(e)}")
        return False


# Función de autenticación (igual que en app.py)
def autenticar_usuario(username: str, password: str) -> bool:
    """Autentica un usuario contra la base de datos"""
    engine = init_login_connection()
    if engine is None:
        st.error("No se pudo conectar a la base de datos de autenticación.")
        return False

    try:
        query = text("""
            SELECT password_hash, sal, activo 
            FROM usuarios 
            WHERE username = :username
        """)

        with engine.connect() as connection:
            result = connection.execute(query, {"username": username}).fetchone()

        if not result:
            st.error("Usuario no encontrado.")
            return False

        hash_almacenado = result[0]
        sal = result[1]
        activo = bool(result[2])

        if not activo:
            st.error("Esta cuenta está desactivada.")
            return False

        if not all([hash_almacenado, sal]):
            st.error("Credenciales inválidas en la base de datos.")
            return False

        if verificar_password(sal, hash_almacenado, password):
            return True

        st.error("Contraseña incorrecta.")
        return False

    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")
        return False


# Funciones de gestión de usuarios (igual que en app.py)
def obtener_info_usuario(username: str):
    """Obtiene información del usuario"""
    engine = init_login_connection()
    if engine is None:
        return None

    try:
        query = text("SELECT id, nombre_completo FROM usuarios WHERE username = :username")
        with engine.connect() as connection:
            result = connection.execute(query, {"username": username}).fetchone()
        return {'id': result[0], 'nombre_completo': result[1]} if result else None
    except Exception as e:
        st.error(f"Error al obtener información del usuario: {e}")
        return None


def cambiar_password(username: str, password_actual: str, nuevo_password: str) -> bool:
    """Cambia la contraseña de un usuario"""
    engine = init_login_connection()
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            # Verificar contraseña actual
            result = connection.execute(
                text("SELECT password_hash, sal FROM usuarios WHERE username = :username"),
                {"username": username}
            ).fetchone()

            if not result:
                st.error("Usuario no encontrado.")
                return False

            hash_almacenado, sal = result[0], result[1]

            if not verificar_password(sal, hash_almacenado, password_actual):
                st.error("La contraseña actual es incorrecta.")
                return False

            # Generar nuevo hash
            nueva_sal, nuevo_hash = crear_hash_con_sal(nuevo_password)
            if not nueva_sal or not nuevo_hash:
                return False

            # Actualizar en base de datos
            connection.execute(
                text("""
                    UPDATE usuarios 
                    SET password_hash = :nuevo_hash, sal = :nueva_sal
                    WHERE username = :username
                """),
                {
                    "nuevo_hash": nuevo_hash,
                    "nueva_sal": nueva_sal,
                    "username": username
                }
            )
            connection.commit()
        st.success("¡Contraseña cambiada exitosamente!")
        return True
    except Exception as e:
        st.error(f"Error al cambiar contraseña: {e}")
        return False


def crear_usuario(username: str, password: str, nombre_completo: str) -> bool:
    """Crea un nuevo usuario en el sistema"""
    engine = init_login_connection()
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            # Verificar si el usuario ya existe
            existe = connection.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE username = :username"),
                {"username": username}
            ).scalar()

            if existe:
                st.error("El nombre de usuario ya existe.")
                return False

            # Crear hash de contraseña
            sal, password_hash = crear_hash_con_sal(password)
            if not sal or not password_hash:
                return False

            # Insertar nuevo usuario
            connection.execute(
                text("""
                    INSERT INTO usuarios (username, password_hash, sal, nombre_completo)
                    VALUES (:username, :password_hash, :sal, :nombre_completo)
                """),
                {
                    "username": username,
                    "password_hash": password_hash,
                    "sal": sal,
                    "nombre_completo": nombre_completo
                }
            )
            connection.commit()
        st.success("Usuario registrado exitosamente!")
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")
        return False


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


# Cargar base de datos interna (el archivo parquet)
@st.cache_data
def cargar_datos(ruta_parquet):
    try:
        df = pd.read_parquet(ruta_parquet)
        df.fillna(0, inplace=True)
        df['Nombre'] = df['Nombre'].astype(str).str.upper()
        df['Documento'] = df['Documento'].astype(str)
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {str(e)}")
        return None


# Plantillas por pestaña
PLANTILLAS = {
    "tab1": {
        "LEGALIZACIÓN RECHAZADA": "legalizacion_rechazada.docx",
        "LEGALIZACIÓN RECHAZADA POR CAMBIO DE COMUNA": "legalizacion_rechazada_cambio_comuna.docx",
        "NO PRESELECCIONADO POR PUNTO DE CORTE PP": "No_preseleccionado_por_punto_corte_pp.docx",
        "NO CUMPLE HABILITANTE ART.70 LITERAL B": "No_cumple_habilitante_b.docx",
        "IMPEDIDO ART. 71 LITERAL A": "Impedido_literal_a.docx",
    },
    "tab2": {
        "NO CUMPLE HABILITANTE ART. 40 LITERAL F DEC. 0344 DE 2025": "No_cumple_habilitante_f_efe.docx",
        "NO CUMPLE HABILITANTE ART. 40 LITERAL G DEC. 0344 DE 2025": "No_cumple_habilitante_g_efe.docx"
    }
}


# Generar documento según plantilla y tipo
def generar_documento(tipo_documento, row, radicado, pestaña, imagen1=None, imagen2=None):
    context = row.to_dict()
    context['radicado'] = radicado  # Agregamos el radicado ingresado

    for key in context:
        if key.startswith('cal'):
            context[key] = formato_numero(context[key])

    template_path = PLANTILLAS[pestaña][tipo_documento]
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


# Componentes de la UI
def mostrar_formulario_login():
    """Muestra el formulario de login"""
    st.title("📄 Generador de PQRS para Convocatorias")
    st.subheader("Sapiencia - Medellín")
    with st.form("login_form"):
        st.markdown("## 🔐 Inicio de Sesión")
        username = st.text_input("Usuario", key="login_username")
        password = st.text_input("Contraseña", type="password", key="login_password")
        submit_button = st.form_submit_button("Iniciar Sesión")

        if submit_button:
            if not username or not password:
                st.error("Por favor complete todos los campos.")
                return

            if autenticar_usuario(username, password):
                st.session_state.autenticado = True
                st.session_state.username = username
                st.session_state.user_info = obtener_info_usuario(username)
                st.success("¡Inicio de sesión exitoso!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")


def mostrar_formulario_cambio_password():
    """Muestra el formulario para cambiar contraseña"""
    with st.form("cambio_password_form"):
        st.markdown("## 🔄 Cambiar Contraseña")
        password_actual = st.text_input("Contraseña actual", type="password")
        nueva_password = st.text_input("Nueva contraseña", type="password")
        confirmar_password = st.text_input("Confirmar nueva contraseña", type="password")
        submit_button = st.form_submit_button("Cambiar Contraseña")

        if submit_button:
            if not all([password_actual, nueva_password, confirmar_password]):
                st.error("Por favor complete todos los campos.")
                return

            if nueva_password != confirmar_password:
                st.error("Las nuevas contraseñas no coinciden.")
            elif len(nueva_password) < 8:
                st.error("La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                cambiar_password(st.session_state.username, password_actual, nueva_password)


def mostrar_formulario_registro():
    """Muestra el formulario de registro de nuevos usuarios"""
    # Solo permitir el registro si el usuario es 'admin'
    if st.session_state.username == 'admin':
        with st.form("registro_form"):
            st.markdown("## 📝 Registrar Nuevo Usuario")
            nuevo_username = st.text_input("Nombre de usuario")
            nuevo_nombre = st.text_input("Nombre completo")
            nueva_password = st.text_input("Contraseña", type="password")
            confirmar_password = st.text_input("Confirmar contraseña", type="password")
            submit_button = st.form_submit_button("Registrar Usuario")

            if submit_button:
                if not all([nuevo_username, nuevo_nombre, nueva_password, confirmar_password]):
                    st.error("Por favor complete todos los campos.")
                    return

                if nueva_password != confirmar_password:
                    st.error("Las contraseñas no coinciden.")
                elif len(nueva_password) < 8:
                    st.error("La contraseña debe tener al menos 8 caracteres.")
                else:
                    crear_usuario(nuevo_username, nueva_password, nuevo_nombre)
    else:
        st.warning("🚨 Solo el usuario 'admin' puede registrar nuevos usuarios.")


def mostrar_interfaz_principal_pqrs():
    """Muestra la interfaz principal de PQRS después del login"""
    st.title("📄 Generador de PQRS para Convocatorias")
    st.subheader(f"Sapiencia - Medellín | Usuario: {st.session_state.username}")

    # Menú de opciones
    menu_options = ["Generar PQRS", "Cambiar contraseña"]
    if st.session_state.username == 'admin':
        menu_options.append("Registrar usuario")
    menu_options.append("Cerrar sesión")

    opcion = st.sidebar.selectbox(
        "Menú",
        menu_options
    )

    if opcion == "Generar PQRS":
        # Configuración de pestañas
        tab1, tab2, tab3 = st.tabs([
            "📄 Línea Pregrado",
            "📄 Posgrado - Extendiendo Fronteras",
            "📄 Posgrados maestros - Formación Avanzada"
        ])

        with tab1:
            st.header("Línea Pregrado")
            ruta_parquet = "/app/Resultados_Linea_pregrado_2025-2.parquet"
            df = cargar_datos(ruta_parquet)

            if df is not None:
                st.success(f"Base de datos cargada con {len(df)} registros.")
                doc_busqueda = st.text_input("🔎 Ingrese el número de documento del aspirante:", key="doc_pregrado")
                resultado = df[df['Documento'] == doc_busqueda] if doc_busqueda else pd.DataFrame()

                if not resultado.empty:
                    row = resultado.iloc[0]
                    st.success(f"Aspirante encontrado: {row['Nombre']}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**Documento:** {row['Documento']}")
                    with col2:
                        st.info(f"**Comuna:** {row['Comuna']}")
                        st.info(f"**Estrato:** {row['Estrato']}")
                    with col3:
                        st.info(f"**Puntaje total:** {row['cal_total']}")
                        st.info(f"**Punto de corte PP:** {row['punto_corte_pp']}")
                        st.info(f"**Resultado PP:** {row['Observaciones Presupuesto Participativo']}")

                    # Campo radicado (antes de seleccionar plantilla)
                    radicado = st.text_input("✍️ Ingrese el número de radicado:", max_chars=30, key="rad_pregrado")

                    # Selección de tipo de documento
                    tipo_documento = st.selectbox(
                        "📄 Seleccione el tipo de documento a generar:",
                        list(PLANTILLAS["tab1"].keys()),
                        key="tipo_doc_pregrado"
                    )

                    # Subida de imágenes
                    if tipo_documento == "NO PRESELECCIONADO POR PUNTO DE CORTE PP":
                        st.markdown("📷 Suba las dos imágenes requeridas para el documento:")
                        imagen1 = st.file_uploader("Imagen 1 (para {{imagen_1}})", type=["jpg", "jpeg", "png"],
                                                   key="img1_pregrado")
                        imagen2 = st.file_uploader("Imagen 2 (para {{imagen_2}})", type=["jpg", "jpeg", "png"],
                                                   key="img2_pregrado")
                    else:
                        st.markdown("📷 Suba la imagen requerida para el documento:")
                        imagen1 = st.file_uploader("Imagen 1 (para {{imagen_1}})", type=["jpg", "jpeg", "png"],
                                                   key="img1_pregrado")
                        imagen2 = None

                    # Botón para generar
                    if st.button("✅ Generar Documento", key="btn_pregrado"):
                        if not radicado.strip():
                            st.warning("Debe ingresar el número de radicado.")
                        elif tipo_documento == "NO PRESELECCIONADO POR PUNTO DE CORTE PP" and (
                                imagen1 is None or imagen2 is None):
                            st.warning("Debe subir ambas imágenes.")
                        elif tipo_documento != "NO PRESELECCIONADO POR PUNTO DE CORTE PP" and imagen1 is None:
                            st.warning("Debe subir una imagen.")
                        else:
                            buffer = generar_documento(tipo_documento, row, radicado, "tab1", imagen1, imagen2)
                            nombre_doc = f"{tipo_documento.replace(' ', '_')}_{row['Documento']}_{row['Nombre'][:20]}.docx"

                            st.download_button(
                                label="📥 Descargar Documento",
                                data=buffer,
                                file_name=nombre_doc,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                elif doc_busqueda:
                    st.warning("No se encontró ningún aspirante con ese documento.")

        with tab2:
            st.header("Posgrado - Extendiendo Fronteras")
            ruta_parquet = "/app/Resultados_EFE_2025-2.parquet"
            df = cargar_datos(ruta_parquet)

            if df is not None:
                st.success(f"Base de datos cargada con {len(df)} registros.")
                doc_busqueda = st.text_input("🔎 Ingrese el número de documento del aspirante:", key="doc_posgrado")
                resultado = df[df['Documento'] == doc_busqueda] if doc_busqueda else pd.DataFrame()

                if not resultado.empty:
                    row = resultado.iloc[0]
                    st.success(f"Aspirante encontrado: {row['Nombre']}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**Documento:** {row['Documento']}")
                    with col2:
                        st.info(f"**Comuna:** {row['Comuna']}")
                        st.info(f"**Estrato:** {row['Estrato']}")
                    with col3:
                        st.info(f"**Puntaje total:** {row['cal_total']}")
                        st.info(f"**Punto de corte PP:** {row['punto_corte_pp']}")
                        st.info(f"**Resultado PP:** {row['Observaciones Presupuesto Participativo']}")

                    # Campo radicado
                    radicado = st.text_input("✍️ Ingrese el número de radicado:", max_chars=30, key="rad_posgrado")

                    # Selección de tipo de documento
                    tipo_documento = st.selectbox(
                        "📄 Seleccione el tipo de documento a generar:",
                        list(PLANTILLAS["tab2"].keys()),
                        key="tipo_doc_posgrado"
                    )

                    # Botón para generar
                    if st.button("✅ Generar Documento", key="btn_posgrado"):
                        if not radicado.strip():
                            st.warning("Debe ingresar el número de radicado.")
                        else:
                            buffer = generar_documento(tipo_documento, row, radicado, "tab2")
                            nombre_doc = f"{tipo_documento.replace(' ', '_')}_{row['Documento']}_{row['Nombre'][:20]}.docx"

                            st.download_button(
                                label="📥 Descargar Documento",
                                data=buffer,
                                file_name=nombre_doc,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                elif doc_busqueda:
                    st.warning("No se encontró ningún aspirante con ese documento.")

        with tab3:
            st.header("Posgrados maestros - Formación Avanzada")
            st.info("Módulo en desarrollo - Próximamente disponible")

    elif opcion == "Cambiar contraseña":
        mostrar_formulario_cambio_password()
    elif opcion == "Registrar usuario":
        mostrar_formulario_registro()
    elif opcion == "Cerrar sesión":
        if st.sidebar.button("Confirmar cierre de sesión"):
            del st.session_state.autenticado
            del st.session_state.username
            del st.session_state.user_info
            st.rerun()


# Punto de entrada de la aplicación
if __name__ == "__main__":
    # Inicializar estado de sesión
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    # Mostrar contenido según autenticación
    if st.session_state.autenticado:
        mostrar_interfaz_principal_pqrs()
    else:
        mostrar_formulario_login()