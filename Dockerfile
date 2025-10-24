# Usa uma imagem leve com Python
FROM python:3.11-slim

# Instala Tesseract e dependências
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    poppler-utils \
    && apt-get clean

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Executa o bot
CMD ["python", "bot.py"]
