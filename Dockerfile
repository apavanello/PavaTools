# Etapa 1: Usar uma imagem base oficial e leve do Python
FROM python:3.13-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential cmake && rm -rf /var/lib/apt/lists/*


ENV UV_PROJECT_ENVIRONMENT=/usr/local
# Atualiza o pip e instala o 'uv'
# Usamos o pip apenas para esta etapa inicial (bootstrapping)
RUN pip install --upgrade pip && pip install uv

# Copia o arquivo de dependências para o diretório de trabalho
ADD pyproject.toml uv.lock /app/

# Instala as dependências usando 'uv'
RUN uv sync 

# Copia o código da sua aplicação para dentro do container
# Nota: No nosso caso com docker-compose e volumes, esta linha não é
# estritamente necessária para desenvolvimento, mas é uma boa prática
# para criar imagens de produção auto-contidas.
COPY ./src/1_Home.py .

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando para executar a aplicação Streamlit quando o container iniciar
# O arquivo principal é "1_Home.py"
CMD ["streamlit", "run", "1_Home.py", "--server.port=8501", "--server.address=0.0.0.0"]