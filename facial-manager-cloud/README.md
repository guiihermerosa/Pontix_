# Pontix Cloud - Sistema de Ponto em Nuvem

Pontix Cloud é uma solução completa de gestão de ponto eletrônico com dois componentes principais:

1. **Sistema Local** - Aplicação desktop/web para registro de ponto facial
2. **Sistema Cloud** - Dashboard multi-empresa para contadores e proprietários

---

## 📋 Arquitetura

```
Pontix Cloud
├── facial-manager (Sistema Local - SQLite)
│   ├── Backend: FastAPI (porta 8000)
│   ├── Frontend: Jinja2 Templates
│   └── Banco de Dados: SQLite
│
└── facial-manager-cloud (Sistema Cloud - Supabase)
    ├── Backend: FastAPI (porta 8001)
    ├── Frontend: Vue 3 (porta 3000)
    └── Banco de Dados: Supabase PostgreSQL
```

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.10+
- Node.js 18+
- Git
- Supabase conta (para produção)

### Instalação - Backend Cloud

```bash
cd facial-manager-cloud/backend

# Criar ambiente virtual
python -m venv venv
source venv/Scripts/Activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações (localhost para desenvolvimento)

# Criar banco de dados
python migrations.py create

# Rodar servidor
python run.py
```

O backend estará disponível em `http://localhost:8001`

### Instalação - Frontend Cloud

```bash
cd facial-manager-cloud/frontend

# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.example .env
# VITE_API_URL=http://localhost:8001

# Rodar desenvolvimento
npm run dev
```

O frontend estará disponível em `http://localhost:5173`

---

## 🔧 Configuração

### Backend - Arquivo .env

```env
# Desenvolvimento
DEBUG=False
REQUIRE_AUTH=False
APP_URL=http://localhost:8001
WEB_APP_URL=http://localhost:5173

# Supabase (para produção)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-publica
SUPABASE_SERVICE_KEY=sua-chave-service-role

# JWT
JWT_SECRET_KEY=sua-chave-secreta-muito-longa
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (Resend)
RESEND_API_KEY=re_sua_chave
RESEND_FROM_EMAIL=noreply@pontix.com

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

### Frontend - Arquivo .env

```env
VITE_API_URL=http://localhost:8001
VITE_APP_NAME=Pontix Cloud
```

---

## 📚 API Endpoints

### Autenticação

```
POST   /api/auth/register      - Registrar novo usuário
POST   /api/auth/login         - Fazer login
POST   /api/auth/refresh       - Renovar token
GET    /api/auth/me            - Dados do usuário atual
POST   /api/auth/logout        - Logout
```

### Painel do Contador

```
GET    /api/accounting/dashboard           - Dashboard com estatísticas
GET    /api/accounting/employees           - Listagem de funcionários
GET    /api/accounting/time-records        - Registros de ponto
GET    /api/accounting/occurrences         - Ocorrências
POST   /api/accounting/occurrences         - Criar ocorrência
PUT    /api/accounting/occurrences/{id}    - Atualizar ocorrência
GET    /api/accounting/justifications      - Justificativas
```

### Painel do Proprietário

```
GET    /api/owner/dashboard                 - Dashboard com visão geral
GET    /api/owner/companies                 - Listagem de empresas
GET    /api/owner/companies/{id}            - Detalhes da empresa
PUT    /api/owner/companies/{id}            - Atualizar empresa
GET    /api/owner/companies/{id}/users      - Usuários da empresa
POST   /api/owner/companies/{id}/users/invite - Convidar usuário
GET    /api/owner/companies/{id}/statistics - Estatísticas
```

### Sincronização

```
POST   /api/sync/employees      - Sincronizar funcionários
POST   /api/sync/time-records   - Sincronizar registros de ponto
POST   /api/sync/occurrences    - Sincronizar ocorrências
GET    /api/sync/status/{id}    - Status de sincronização
```

---

## 🧪 Testes

### Testar Backend com Mock Data

```bash
cd backend

# Instalar dependência de teste
pip install httpx

# Executar testes
python test_api.py
```

Isso executará uma suite completa de testes incluindo:
- Health check
- Registro e login
- Endpoints do contador
- Endpoints do proprietário
- Sincronização de dados

---

## 📦 Modelos de Dados

### Empresa (Company)

```python
{
    "id": "UUID",
    "name": "Nome da Empresa",
    "cnpj": "XX.XXX.XXX/XXXX-XX",
    "owner_id": "user-id",
    "email": "contato@empresa.com",
    "phone": "+55 11 9999-9999",
    "address": "Rua X, 123",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "01000-000",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### Funcionário (Employee)

```python
{
    "id": "UUID",
    "company_id": "UUID",
    "user_id": "001",
    "full_name": "Nome do Funcionário",
    "email": "func@empresa.com",
    "cpf": "123.456.789-00",
    "department": "TI",
    "role": "Developer",
    "registration_number": "EMP001",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
}
```

### Registro de Ponto (TimeRecord)

```python
{
    "id": "UUID",
    "company_id": "UUID",
    "employee_id": "UUID",
    "user_id": "001",
    "record_date": "2024-01-15T08:30:00Z",
    "record_time": "08:30:00",
    "record_type": "entry",  # entry, exit, break_start, break_end
    "source": "device",      # device, manual, adjusted
    "is_adjusted": false,
    "created_at": "2024-01-15T08:30:00Z"
}
```

### Ocorrência (Occurrence)

```python
{
    "id": "UUID",
    "company_id": "UUID",
    "employee_id": "UUID",
    "occurrence_date": "2024-01-15T00:00:00Z",
    "occurrence_type": "late",  # late, absence, early_exit, etc
    "severity": "medium",       # low, medium, high, critical
    "description": "Chegou 15 minutos atrasado",
    "status": "pending",        # pending, reviewed, resolved, dismissed
    "created_at": "2024-01-15T08:30:00Z"
}
```

---

## 🔐 Autenticação

O sistema usa **JWT (JSON Web Tokens)** para autenticação:

1. **Registro/Login**: Usuário recebe um `access_token`
2. **Requisições**: Token é incluído no header `Authorization: Bearer <token>`
3. **Middleware**: Valida token e injeta dados do usuário na requisição
4. **Expiração**: Token expira em 30 minutos (configurável)

### Exemplo de Uso

```javascript
// Obter token
const response = await api.post('/api/auth/login', {
    email: 'user@example.com',
    password: 'password'
});
const token = response.data.access_token;

// Armazenar token
localStorage.setItem('access_token', token);

// Usar token em requisições
const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
};
```

---

## 🚢 Deploy

### Deploy Backend - Render

1. **Criar conta** em https://render.com
2. **Conectar repositório Git**
3. **Criar novo serviço Web**:
   - Language: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python run.py`
   - Port: 8001
   - Environment: Production
4. **Configurar variáveis de ambiente**:
   - REQUIRE_AUTH=True
   - SUPABASE_URL=...
   - SUPABASE_KEY=...
   - JWT_SECRET_KEY=... (usar valor seguro)

### Deploy Frontend - Vercel

1. **Criar conta** em https://vercel.com
2. **Conectar repositório Git**
3. **Criar novo projeto**:
   - Framework: Vue
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. **Configurar variáveis**:
   - VITE_API_URL=https://api-pontix-cloud.render.com

### Setup Supabase

1. **Criar projeto** em https://supabase.com
2. **Notar credenciais**:
   - Project URL (SUPABASE_URL)
   - Anon Public Key (SUPABASE_KEY)
   - Service Role Key (SUPABASE_SERVICE_KEY)
3. **Executar migrações** (em produção):
   ```bash
   python migrations.py create
   ```

---

## 🐛 Troubleshooting

### Erro de Conexão com Banco de Dados

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solução**: Verificar SUPABASE_URL e credenciais no .env

### Token Expirado

```
{"detail": "Token inválido"}
```

**Solução**: Fazer login novamente para obter novo token

### CORS Error

```
Access to XMLHttpRequest blocked by CORS policy
```

**Solução**: Verificar CORS_ORIGINS no .env do backend

### Porta já em uso

```
Address already in use
```

**Solução**: Mudar porta no comando de execução:
```bash
python run.py --port 8002
```

---

## 📝 Estrutura de Diretórios

### Backend

```
backend/
├── app/
│   ├── api/
│   │   ├── routes_auth.py
│   │   ├── routes_accounting.py
│   │   ├── routes_owner.py
│   │   └── routes_sync.py
│   ├── auth/
│   │   └── middleware.py
│   ├── database/
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/
│   │   └── common.py
│   ├── config.py
│   └── main.py
├── migrations.py
├── run.py
└── requirements.txt
```

### Frontend

```
frontend/
├── src/
│   ├── pages/
│   │   ├── AccountingDashboard.vue
│   │   └── OwnerDashboard.vue
│   ├── services/
│   │   └── api.js
│   ├── router/
│   │   └── index.js
│   ├── App.vue
│   └── main.js
├── package.json
└── vite.config.js
```

---

## 🔄 Fluxo de Sincronização

```
Sistema Local (8000)          Sistema Cloud (8001)
      ↓                              ↓
  SQLite DB              ← Sincroniza →     Supabase PostgreSQL
      ↓                              ↓
  Funcionários          ← Envia dados →     Dashboard Contador
  Registros de Ponto    ← Recebe dados →    Dashboard Proprietário
  Ocorrências
```

### Processo de Sincronização

1. **Local → Cloud**:
   - Sistema local coleta dados
   - Envia para `/api/sync/employees`, `/api/sync/time-records`, etc
   - Cloud valida e armazena em Supabase

2. **Cloud → Local** (Futuro):
   - Dashboard cloud faz alterações
   - Notifica sistema local via webhooks
   - Sistema local atualiza SQLite

---

## 📞 Suporte

Para problemas, consultar:
- Documentação da API em `/docs` (Swagger)
- Logs em `logs/pontix-cloud.log`
- Issues no repositório Git

---

## 📄 Licença

Pontix Cloud © 2024. Todos os direitos reservados.

---

## 🎯 Roadmap

- [ ] Autenticação com Supabase Auth
- [ ] Dashboard de relatórios avançados
- [ ] Exportação de dados (Excel, PDF)
- [ ] Webhooks para eventos
- [ ] Mobile app (React Native)
- [ ] Integração com sistemas de folha de pagamento
- [ ] Biometria avançada (facial + iris)
- [ ] Escalação automática em Render

