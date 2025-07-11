# Usa una imagen base liviana con Python 3.11
FROM python:3.11-slim

# Instala dependencias del sistema necesarias para pyarrow (usado por pandas para leer parquet)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Crea el directorio de trabajo
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY pqrs.py /app/
COPY legalizacion_rechazada.docx /app/
COPY No_preseleccionado_por_punto_corte_pp.docx /app/
COPY No_cumple_habilitante_b.docx /app/

# Instala las dependencias de Python
RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    numpy \
    docxtpl \
    python-docx \
    num2words \
    pyarrow

# Expone el puerto por defecto de Streamlit
EXPOSE 8501

# Comando para ejecutar la app de Streamlit
CMD ["streamlit", "run", "pqrs.py", "--server.port=8501", "--server.address=0.0.0.0"]
