# Dockerfile
FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos da aplicação
COPY app.py camera_model.py drive_client.py record.py cleanup.py utils.py client_secrets.json requirements.txt /app/
COPY token.json client_secrets.json ./shared/

# Instala dependências do Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Exponha a porta do Streamlit (frontend)
EXPOSE 8501

# Comando padrão pode ser sobrescrito no docker-compose
CMD ["streamlit", "run", "app.py"]
