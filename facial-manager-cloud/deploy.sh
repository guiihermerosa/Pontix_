#!/bin/bash

# Script de deployment automatizado para Pontix Cloud
# Configura e faz deploy para Render e Vercel

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║       🚀 PONTIX CLOUD - DEPLOYMENT AUTOMATION                 ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cor
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verificar pré-requisitos
check_prerequisites() {
    log_info "Verificando pré-requisitos..."
    
    # Git
    if ! command -v git &> /dev/null; then
        log_error "Git não encontrado. Por favor, instale Git."
        exit 1
    fi
    log_success "Git encontrado"
    
    # Node.js
    if ! command -v node &> /dev/null; then
        log_warn "Node.js não encontrado. Será necessário para o frontend."
    else
        log_success "Node.js encontrado: $(node --version)"
    fi
    
    # Python
    if ! command -v python3 &> /dev/null; then
        log_warn "Python 3 não encontrado. Será necessário para o backend."
    else
        log_success "Python 3 encontrado: $(python3 --version)"
    fi
}

# Solicitar informações do usuário
get_user_input() {
    log_info "Configurando variáveis de deployment..."
    echo ""
    
    read -p "  Digite seu Supabase Project URL [https://seu-projeto.supabase.co]: " SUPABASE_URL
    SUPABASE_URL=${SUPABASE_URL:-https://seu-projeto.supabase.co}
    
    read -sp "  Digite sua Supabase Anon Public Key: " SUPABASE_KEY
    echo ""
    
    read -sp "  Digite sua Supabase Service Role Key: " SUPABASE_SERVICE_KEY
    echo ""
    
    read -p "  Digite seu JWT Secret Key (ou deixe em branco para gerar): " JWT_SECRET_KEY
    if [ -z "$JWT_SECRET_KEY" ]; then
        JWT_SECRET_KEY=$(openssl rand -base64 32)
        log_success "JWT Secret Key gerado: ${JWT_SECRET_KEY:0:20}..."
    fi
    
    read -p "  Digite seu Resend API Key (deixe em branco se não usar): " RESEND_API_KEY
    
    read -p "  Digite seu Email do Resend [noreply@pontix.com]: " RESEND_FROM_EMAIL
    RESEND_FROM_EMAIL=${RESEND_FROM_EMAIL:-noreply@pontix.com}
    
    read -p "  Digite o URL da sua aplicação no Render (ex: https://pontix-api.onrender.com): " APP_URL
    
    read -p "  Digite o URL da sua aplicação no Vercel (ex: https://pontix.vercel.app): " WEB_APP_URL
    
    echo ""
}

# Criar arquivos .env
create_env_files() {
    log_info "Criando arquivos de ambiente..."
    
    # Backend .env
    cat > facial-manager-cloud/backend/.env << EOF
DEBUG=False
REQUIRE_AUTH=True
APP_URL=${APP_URL}
WEB_APP_URL=${WEB_APP_URL}

SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}

JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

LOCAL_SYSTEM_URL=http://localhost:8000
LOCAL_SYSTEM_API_KEY=

RESEND_API_KEY=${RESEND_API_KEY}
RESEND_FROM_EMAIL=${RESEND_FROM_EMAIL}
RESEND_FROM_NAME=Pontix Cloud

CORS_ORIGINS=${WEB_APP_URL},http://localhost:5173,http://localhost:3000
ALLOWED_HOSTS=localhost

LOG_LEVEL=INFO
LOG_FILE=logs/pontix-cloud.log
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5
EOF
    
    log_success "Backend .env criado"
    
    # Frontend .env
    cat > facial-manager-cloud/frontend/.env << EOF
VITE_API_URL=${APP_URL}
VITE_APP_NAME=Pontix Cloud
EOF
    
    log_success "Frontend .env criado"
}

# Testar backend localmente
test_backend() {
    log_info "Testando backend localmente..."
    
    if ! command -v python3 &> /dev/null; then
        log_warn "Python 3 não encontrado, pulando testes do backend"
        return
    fi
    
    cd facial-manager-cloud/backend
    
    # Criar ambiente virtual
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Ativar ambiente virtual
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    
    # Instalar dependências
    pip install -q -r requirements.txt
    
    # Testar imports
    python3 -c "from app.main import app; print('✓ Backend OK')" && log_success "Backend imports OK" || log_error "Backend import failed"
    
    cd ../..
}

# Testar frontend localmente
test_frontend() {
    log_info "Testando frontend localmente..."
    
    if ! command -v npm &> /dev/null; then
        log_warn "npm não encontrado, pulando testes do frontend"
        return
    fi
    
    cd facial-manager-cloud/frontend
    
    npm install --quiet
    npm run build --quiet && log_success "Frontend build OK" || log_error "Frontend build failed"
    
    cd ../..
}

# Configurar Git
setup_git() {
    log_info "Configurando Git..."
    
    git config user.email "pontix@example.com" 2>/dev/null || true
    git config user.name "Pontix Deployment" 2>/dev/null || true
    
    log_success "Git configurado"
}

# Gerar instruções finais
print_instructions() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║             ✅ CONFIGURAÇÃO COMPLETA!                         ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}Próximos passos:${NC}"
    echo ""
    echo "1️⃣  ${BLUE}Configurar Render (Backend)${NC}"
    echo "   • Acesse https://render.com"
    echo "   • Crie um novo Web Service"
    echo "   • Conecte seu repositório GitHub"
    echo "   • Build Command: pip install -r requirements.txt && python migrations.py create"
    echo "   • Start Command: python run.py"
    echo "   • Adicione as variáveis de ambiente do arquivo .env"
    echo ""
    echo "2️⃣  ${BLUE}Configurar Vercel (Frontend)${NC}"
    echo "   • Acesse https://vercel.com"
    echo "   • Importe seu projeto"
    echo "   • Root Directory: frontend"
    echo "   • Build Command: npm run build"
    echo "   • Output Directory: dist"
    echo "   • Adicione VITE_API_URL: ${APP_URL}"
    echo ""
    echo "3️⃣  ${BLUE}Deploy${NC}"
    echo "   • Faça push para main: git push origin main"
    echo "   • Render e Vercel farão deploy automático"
    echo ""
    echo "4️⃣  ${BLUE}Verificar${NC}"
    echo "   • Backend health: ${APP_URL}/health"
    echo "   • Frontend: ${WEB_APP_URL}"
    echo "   • Documentação API: ${APP_URL}/docs"
    echo ""
    echo -e "${GREEN}Variáveis de ambiente salvas em:${NC}"
    echo "   • Backend: facial-manager-cloud/backend/.env"
    echo "   • Frontend: facial-manager-cloud/frontend/.env"
    echo ""
}

# Main
main() {
    check_prerequisites
    echo ""
    
    get_user_input
    echo ""
    
    create_env_files
    echo ""
    
    test_backend
    echo ""
    
    test_frontend
    echo ""
    
    setup_git
    echo ""
    
    print_instructions
    
    log_success "Deploy preparado com sucesso!"
}

# Executar main
main
