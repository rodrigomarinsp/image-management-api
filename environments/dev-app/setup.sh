#!/bin/bash

# setup.sh - Script de configuração para o Image Management API
# Este script configura o ambiente, instala dependências e inicializa o banco de dados

# Definir cores para mensagens
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para exibir mensagens com timestamp
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${GREEN}[$timestamp]${NC} $1"
}

error() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${RED}[$timestamp ERROR]${NC} $1" >&2
}

warning() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${YELLOW}[$timestamp WARN]${NC} $1"
}

# Função para verificar se um comando está disponível
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "Comando '$1' não encontrado. Instalando..."
        return 1
    fi
    return 0
}

# Verificar pré-requisitos
log "Verificando pré-requisitos..."

# Detectar se estamos em um ambiente Docker
IN_DOCKER=false
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
    log "Ambiente Docker detectado"
fi

# Verificar e instalar Python
if ! check_command python3; then
    if [ "$IN_DOCKER" = true ]; then
        apt-get update && apt-get install -y python3 python3-pip python3-venv
    else
        error "Python3 não está instalado. Por favor, instale o Python 3.8+ antes de continuar."
        exit 1
    fi
fi

# Garantir que pip esteja disponível
if ! check_command pip; then
    if check_command pip3; then
        log "Usando pip3 em vez de pip"
        alias pip=pip3
    else
        if [ "$IN_DOCKER" = true ]; then
            apt-get update && apt-get install -y python3-pip
        else
            error "pip não está instalado. Por favor, instale pip antes de continuar."
            exit 1
        fi
    fi
fi

# Verificar versão do Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
log "Usando Python $PYTHON_VERSION"

if [ "$(echo "$PYTHON_VERSION" | cut -d. -f1)" -lt 3 ] || [ "$(echo "$PYTHON_VERSION" | cut -d. -f2)" -lt 8 ]; then
    warning "A versão recomendada do Python é 3.8+. Você está usando $PYTHON_VERSION."
fi

# Criar ambiente virtual se não estiver em Docker
if [ "$IN_DOCKER" = false ]; then
    log "Criando ambiente virtual..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        if [ $? -ne 0 ]; then
            error "Falha ao criar ambiente virtual. Verifique sua instalação do Python."
            exit 1
        fi
    else
        log "Ambiente virtual já existe."
    fi

    # Ativar ambiente virtual
    log "Ativando ambiente virtual..."
    source .venv/bin/activate
    if [ $? -ne 0 ]; then
        error "Falha ao ativar ambiente virtual."
        exit 1
    fi
fi

# Instalar dependências
log "Instalando dependências..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        error "Falha ao instalar dependências. Verifique seu arquivo requirements.txt."
        exit 1
    fi
else
    warning "Arquivo requirements.txt não encontrado. Instalando dependências padrão..."
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart pydantic-settings loguru sentence-transformers pinecone-client google-cloud-storage google-cloud-vision pillow python-jose[cryptography] passlib[bcrypt]
    if [ $? -ne 0 ]; then
        error "Falha ao instalar dependências padrão."
        exit 1
    fi
fi

# Criar diretório para armazenamento local
log "Configurando diretório de armazenamento local..."
mkdir -p storage/teams

# Verificar variáveis de ambiente
log "Verificando configuração de ambiente..."
if [ ! -f ".env" ]; then
    log "Criando arquivo .env padrão..."
    cat > .env << EOF
# Configuração do Banco de Dados
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=image_management
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@localhost/image_management # pragma: allowlist secret

# Google Cloud Storage (para produção)
GCS_BUCKET_NAME=
GCS_PROJECT_ID=
GCS_CREDENTIALS_FILE=

# Configurações da API
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
API_KEY_PREFIX=imapi
API_KEY_LENGTH=32
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_VECTOR_SEARCH=false

# Vector Search (para recursos de busca semântica)
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
PINECONE_INDEX_NAME=image-embeddings

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:8000", "http://localhost:3000"]
EOF
    
    warning "Arquivo .env criado com configuração padrão. Edite conforme necessário para seu ambiente."
fi

# Configurar banco de dados
log "Configurando banco de dados..."
if [ "$IN_DOCKER" = true ]; then
    # Em ambiente Docker, esperamos que o banco de dados já esteja configurado ou
    # seja provido por um contêiner separado
    log "Em ambiente Docker: assumindo que o banco de dados está configurado externamente"
else
    # Tentar criar o banco de dados PostgreSQL localmente
    if check_command psql; then
        log "PostgreSQL detectado. Tentando criar banco de dados..."
        
        # Extrair valores do arquivo .env
        DB_NAME=$(grep POSTGRES_DB .env | cut -d= -f2)
        DB_USER=$(grep POSTGRES_USER .env | cut -d= -f2)
        
        # Verificar se o banco já existe
        if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
            log "Banco de dados '$DB_NAME' já existe."
        else
            log "Criando banco de dados '$DB_NAME'..."
            createdb "$DB_NAME" || warning "Falha ao criar banco de dados. Você pode precisar fazê-lo manualmente."
        fi
    else
        warning "PostgreSQL não encontrado. Você precisará criar o banco de dados manualmente."
    fi
fi

# Configuração do banco de dados usando SQLAlchemy
log "Criando tabelas no banco de dados..."
python3 -c "from app.db.session import Base, engine; from app.models.base import *; Base.metadata.create_all(engine)" || {
    error "Falha ao criar tabelas. Verifique sua configuração de banco de dados."
    warning "Continuando mesmo com erro. Você pode precisar inicializar o banco manualmente."
}

# Inicialização de dados
log "Inicializando dados de exemplo..."
python3 -c "from app.db.init_db import init_db; from app.db.session import SessionLocal; db = SessionLocal(); init_db(db); db.close()" || {
    error "Falha ao inicializar dados. Verifique sua configuração de banco de dados."
    warning "Continuando mesmo com erro. Você pode precisar inicializar os dados manualmente."
}

# Criar diretório de armazenamento temporário
log "Criando diretório de armazenamento temporário..."
mkdir -p uploads temp

# Verificar se o aplicativo pode ser iniciado
log "Verificando a configuração do aplicativo..."
if [ -f "run.py" ]; then
    log "Aplicação configurada com sucesso!"
else
    # Criar arquivo run.py se não existir
    log "Criando arquivo run.py básico..."
    cat > run.py << EOF
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
EOF
fi

# Verificar arquivo main.py
if [ ! -f "app/main.py" ]; then
    warning "app/main.py não encontrado. Verifique se a estrutura do projeto está correta."
fi

# Instruções finais
echo 
log "Configuração concluída!"
echo 
log "Para iniciar a aplicação:"
if [ "$IN_DOCKER" = false ]; then
    echo "  1. Ative o ambiente virtual: source .venv/bin/activate"
fi
echo "  2. Inicie o servidor: python run.py"
echo 
log "A API estará disponível em: http://localhost:8000"
log "Documentação Swagger UI: http://localhost:8000/docs"
echo 

exit 0
