# Usa uma imagem oficial do Python otimizada
FROM python:3.11-slim

# Instala ferramentas essenciais do sistema para redes e descompactação
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    p7zip-full \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expõe a porta padrão do JupyterLab
EXPOSE 8888

# Inicia o JupyterLab sem pedir senha/token e permitindo acesso externo
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]