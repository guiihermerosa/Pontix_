# 📱 Pontix — Portal do Contador

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-green) ![Tests](https://img.shields.io/badge/Tests-25/25-brightgreen) ![License](https://img.shields.io/badge/License-MIT-blue)

Sistema integrado de gerenciamento de ponto, ocorrências e justificativas para contadores. Integra dispositivo biométrico local **ALTEK ALPHA-1111** com cloud Supabase para sincronização em tempo real.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   DISPOSITIVO BIOMÉTRICO (ALTEK ALPHA-1111)            │
│   Local Network 192.168.0.24                           │
│              ↓                                          │
│   ┌─────────────────────────────────────────────────┐  │
│   │   API Pontix (FastAPI)                          │  │
│   │   - Sincronização automática                    │  │
│   │   - Detecção de ocorrências                     │  │
│   │   - Gerenciamento de justificativas             │  │
│   │   - Portal do Contador                          │  │
│   └─────────────────────────────────────────────────┘  │
│              ↓                                          │
│   ┌─────────────────────────────────────────────────┐  │
│   │   Supabase PostgreSQL (Cloud)                   │  │
│   │   - Backup centralizado                        │  │
│   │   - Multi-tenant architecture                  │  │
│   │   - RLS (Row Level Security)                   │  │
│   └─────────────────────────────────────────────────┘  │
│              ↓                                          │
│   ┌─────────────────────────────────────────────────┐  │
│   │   Frontend (React/Vite)                         │  │
│   │   - Portal do Contador                         │  │
│   │   - Dashboard                                  │  │
│   │   - Relatórios                                 │  │
│   └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Features

### ✅ Gerenciamento Completo
- **Ocorrências**: Detecção automática de atrasos, faltas, saídas antecipadas
- **Justificativas**: Workflow de aprovação/rejeição com linking
- **Portal do Contador**: Dashboard unificado para N empresas
- **Sincronização**: Bidirecional local ↔ Supabase

### 🔐 Segurança
- ✅ Autenticação JWT obrigatória (Bearer token)
- ✅ Autorização baseada em company_id
- ✅ Isolamento de dados por empresa (IDOR protection)
- ✅ Validação em 3 camadas (middleware → dependency → query)
- ✅ Rate limiting e CORS configurável

### 📊 APIs
- **13 novos endpoints** para ocorrências e justificativas
- **Portal API** com filtros, paginação, estatísticas
- **Documentação Swagger** automática (`/docs`)
- **OpenAPI Schema** (`/openapi.json`)

### 🧪 Qualidade
- **25 testes automatizados** (100% passing ✅)
- **Cobertura**: Detection, CRUD, Workflow, Security, Statistics
- **Fixtures**: In-memory SQLite para isolation

---

## 🚀 Quick Start

### 1️⃣ Development Local

#### Clonar e setup
```bash
git clone https://github.com/guiihermerosa/Pontix_.git
cd facial-manager

# Virtual environment
python -m venv venv
source venv/Scripts/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configurar variáveis
```bash
cp .env.example .env
# Editar .env com suas credenciais Supabase + JWT secret
```

#### Iniciar API
```bash
# Opção A: Uvicorn direto
uvicorn app.main:app --reload

# Opção B: Docker Compose
docker-compose up

# API em http://localhost:8000
# Docs em http://localhost:8000/docs
```

#### Rodar testes
```bash
pytest tests/ -v
# Resultado: 25 passed ✅
```

### 2️⃣ Deploy em Produção

#### Render (API)
```bash
# 1. Conectar GitHub ao Render.com
# 2. Web Service → Select repository
# 3. Build: pip install -r requirements.txt
# 4. Start: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app

# URLs: https://pontix-api.onrender.com
```

#### Vercel (Frontend)
```bash
# 1. Conectar GitHub ao Vercel.com
# 2. New Project → Select repository
# 3. Framework: Vite
# 4. Build: npm run build (frontend/)

# URLs: https://pontix.vercel.app
```

**Veja [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) para guia completo.**

---

## 📡 Endpoints Principais

### Ocorrências (7 endpoints)
```http
GET    /api/v1/occurrences/{company_id}                      # Listar com filtros
GET    /api/v1/occurrences/{company_id}/{occurrence_id}      # Detalhe
PUT    /api/v1/occurrences/{company_id}/{id}/status          # Atualizar status
PUT    /api/v1/occurrences/{company_id}/{id}/assign          # Atribuir
DELETE /api/v1/occurrences/{company_id}/{id}                 # Remover (soft delete)
POST   /api/v1/occurrences/{company_id}/detect               # Detectar automático
GET    /api/v1/occurrences/{company_id}/statistics           # Estatísticas
```

### Justificativas (6 endpoints)
```http
GET    /api/v1/justifications/{company_id}                   # Listar com filtros
GET    /api/v1/justifications/{company_id}/{id}              # Detalhe
POST   /api/v1/justifications/{company_id}                   # Criar
PUT    /api/v1/justifications/{company_id}/{id}/approve      # Aprovar
PUT    /api/v1/justifications/{company_id}/{id}/reject       # Rejeitar
GET    /api/v1/justifications/{company_id}/coverage          # Cobertura de período
```

### Portal do Contador (Dashboard)
```http
GET /api/v1/accountant/me                          # Perfil + empresas
GET /api/v1/accountant/companies                   # Listar empresas
GET /api/v1/accountant/companies/{id}              # Detalhes
GET /api/v1/accountant/companies/{id}/occurrences  # Ocorrências
GET /api/v1/accountant/companies/{id}/justifications # Justificativas
GET /api/v1/accountant/dashboard                   # Stats agregadas
```

---

## 📁 Estrutura

```
facial-manager/
├── app/
│   ├── api/                          # Endpoints
│   │   ├── routes_occurrences.py        # 7 endpoints
│   │   ├── routes_justifications.py     # 6 endpoints
│   │   ├── routes_accountant.py         # Portal
│   │   └── ... (outros routers)
│   ├── services/                     # Lógica de negócio
│   │   ├── occurrence_service.py        # Detecção + CRUD
│   │   ├── justification_service.py     # Workflow
│   │   ├── sync_service.py              # Sincronização
│   │   └── ... (outros)
│   ├── database/                     # ORM
│   │   ├── models.py                    # SQLite (local)
│   │   ├── models_supabase.py           # PostgreSQL (cloud)
│   │   └── database.py                  # Conexões
│   ├── auth/                         # Autenticação
│   │   ├── middleware.py                # JWT validation
│   │   ├── permissions.py               # Roles
│   │   └── ...
│   ├── main.py                       # App FastAPI
│   └── dependencies.py               # DI container
├── tests/
│   ├── test_occurrence_justification.py  # 25 tests
│   └── ...
├── static/                           # Assets
├── app/templates/                    # HTML templates
│
├── Dockerfile                        # Container
├── docker-compose.yml                # Local dev
├── Procfile                          # Render config
├── render.yaml                       # Render deployment
│
├── requirements.txt                  # Dependências
├── .env.example                      # Variáveis (template)
├── .gitignore
├── README.md                         # Este arquivo
└── DEPLOYMENT_GUIDE.md               # Guia deployment
```

---

## 🛠 Stack Tecnológico

| Camada | Tecnologia | Version |
|--------|-----------|---------|
| **Framework** | FastAPI | 0.115.5 |
| **Server** | Uvicorn + Gunicorn | 0.32.1 |
| **DB Local** | SQLite | Built-in |
| **DB Cloud** | PostgreSQL (Supabase) | 15+ |
| **ORM** | SQLAlchemy | 2.0.36 |
| **Autenticação** | JWT (PyJWT) | 2.10.0 |
| **Validação** | Pydantic | 2.10.1 |
| **Testing** | Pytest | 8.3.4 |
| **Deploy** | Docker, Render, Vercel | Latest |

---

## 🔑 Variáveis de Ambiente

Veja [.env.example](./.env.example) para template completo.

**Essenciais:**
```env
# Supabase (Cloud DB)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key

# Autenticação
JWT_SECRET_KEY=gerado-com-secrets-token-urlsafe
JWT_ALGORITHM=HS256

# Banco Local
DATABASE_URL=sqlite:///./data/facial.db

# Resend (Email)
RESEND_API_KEY=re_your_api_key

# CORS
CORS_ORIGINS=http://localhost:3000,https://pontix.vercel.app
```

---

## 🧪 Testes

```bash
# Rodar tudo
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=app --cov-report=html

# Teste específico
pytest tests/test_occurrence_justification.py::TestOccurrenceDetection -v

# Watch mode
pytest tests/ -v --tb=short --looponfail
```

**Resultados:** ✅ 25/25 tests passing

---

## 📊 Funcionalidades Principais

### Detecção de Ocorrências
- **Late arrival**: Entrada > 5 minutos após horário
- **Early exit**: Saída > 5 minutos antes do horário
- **Absence**: Sem registros no dia
- **Incomplete day**: Faltou entrada OU saída
- Configurável por empresa (work_hours JSON)

### Justificativas
- **Tipos**: Medical, personal, work_related, court_order, other
- **Workflow**: pending → approved/rejected
- **Linking**: Automático com ocorrências
- **Coverage**: Validar cobertura para período

### Portal do Contador
- **Multi-empresa**: 1 contador → N empresas
- **Isolamento**: Cada empresa vê seus dados
- **Stats**: Ocorrências, justificativas, períodos abertos
- **Filtros**: Por status, tipo, severidade, employee, datas

---

## 🔐 Segurança

### 3 Camadas de Validação

```
1. MIDDLEWARE LAYER (JWT)
   ↓ Valida Bearer token
   
2. DEPENDENCY LAYER (Company Access)
   ↓ Verifica company_id ownership
   
3. QUERY LAYER (Data Isolation)
   ↓ Filtra WHERE company_id = ?
```

### Proteções
- ✅ IDOR (Insecure Direct Object Reference) — bloqueado
- ✅ Data leakage — isolamento por company
- ✅ Unauthorized access — JWT + company check
- ✅ Rate limiting — Slowapi
- ✅ CORS — restritivo por padrão

---

## 📝 Documentação

- **Swagger UI**: `/docs` (Interativo)
- **ReDoc**: `/redoc` (ReadOnly)
- **OpenAPI Schema**: `/openapi.json`
- **Deployment**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Facial Device API**: [docs/FACIAL_API.md](./docs/FACIAL_API.md)

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/sua-feature`)
3. Commit suas mudanças (`git commit -m 'Add sua-feature'`)
4. Push para a branch (`git push origin feature/sua-feature`)
5. Abra um Pull Request

---

## 📈 Task Status

### Completo ✅
- [x] OccurrenceService (detecção + CRUD)
- [x] JustificationService (workflow)
- [x] API endpoints (13 totais)
- [x] Portal do Contador
- [x] Testes (25 casos)
- [x] Segurança (3 camadas)
- [x] Docker setup
- [x] Deployment config

### Próximas Fases 🎯
- [ ] Sync local → Supabase (bidirecional)
- [ ] Audit logging (Supabase table)
- [ ] Email notifications (Resend)
- [ ] RLS policies (Supabase)
- [ ] Frontend React completo
- [ ] Mobile app (React Native)
- [ ] Relatórios mensais (PDF export)

---

## 📄 Licença

MIT License — veja [LICENSE](./LICENSE) para detalhes.

---

## 📞 Contato & Support

- **Email**: support@pontix.dev
- **Issues**: [GitHub Issues](https://github.com/guiihermerosa/Pontix_/issues)
- **Documentation**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

---

**Desenvolvido com ❤️ para contadores, RH e empresas**

🚀 [Acesse Production](https://pontix.vercel.app) | 📚 [API Docs](https://pontix-api.onrender.com/docs)
