# Imagen base con Python 3.10
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos al contenedor
COPY . /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev \
    build-essential python3-dev libxml2-dev libxslt1-dev zlib1g-dev \
    libjpeg-dev libpq-dev gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear archivo de requerimientos
RUN pip install --upgrade pip
RUN pip install streamlit sqlalchemy mysql-connector-python pandas python-docx docxtpl num2words openpyxl

# Exponer el puerto de Streamlit
EXPOSE 8501

# Comando por defecto
CMD ["streamlit", "run", "pqrs.py", "--server.port=8501", "--server.address=0.0.0.0"]
