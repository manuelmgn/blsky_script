# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app
COPY . /app

# Copia el archivo de requisitos y el código fuente
COPY requirements.txt .
COPY main.py .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el archivo de variables de entorno
COPY .env .

# Comando para ejecutar la aplicación
#C MD ["python3", "main.py"]
