# 🚀 Guia de Deployment — Pontix Portal do Contador

## Visão Geral

Este documento descreve como fazer deploy da API Pontix no Render e do frontend no Vercel.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Usuários (Web/Mobile)                                     │
│          ↓                                                   │
│   ┌──────────────────────────────────────┐                 │
│   │     Vercel Frontend (React)          │                 │
│   │  https://pontix.vercel.app           │                 │
│   └──────────────────────────────────────┘                 │
│          ↓ (API calls)                                      │
│   ┌──────────────────────────────────────┐                 │
│   │     Render API (FastAPI)             │                 │
│   │  https://pontix-api.onrender.com     │                 │
│   └──────────────────────────────────────┘                 │
│          ↓                                                   │
│   ┌──────────────────────────────────────┐                 │
│   │     Supabase PostgreSQL              │                 │
│   │  Cloud Database                      │                 │
│   └──────────────────────────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 1: Deploy API no Render

### Pré-requisitos
- Conta no [Render.com](https://render.com)
- Repositório no GitHub (feito ✅)
- Variáveis de ambiente (Supabase, JWT)

### Passo 1: Conectar GitHub ao Render

1. Acesse [https://dashboard.render.com](https://dashboard.render.com)
2. Clique em **"New +"** → **"Web Service"**
3. Conecte sua conta GitHub
4. Selecione o repositório `Pontix_` (ou `Gerenciador_de_ponto`)
5. Configure:
   - **Name**: `pontix-api`
   - **Runtime**: `Python 3.12`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT app.main:app`
   - **Plan**: Free ou Paid (recomendado: Starter para produção)

### Passo 2: Configurar Variáveis de Ambiente

No Render Dashboard, vá para **Environment**:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SECRET_KEY=your-jwt-secret-key
LOG_LEVEL=info
CORS_ORIGINS=https://pontix.vercel.app,https://localhost:3000
```

### Passo 3: Deploy

1. Clique em **"Create Web Service"**
2. Render iniciará o build automaticamente
3. Aguarde 3-5 minutos
4. Seu API estará disponível em `https://pontix-api.onrender.com`

### Verificar Deploy

```bash
# Health check
curl https://pontix-api.onrender.com/health

# Documentação Swagger
https://pontix-api.onrender.com/docs

# OpenAPI Schema
https://pontix-api.onrender.com/openapi.json
```

### Monitor Logs
- Render Dashboard → Logs
- Ou via CLI: `render logs --service-id=xxx`

---

## Part 2: Preparar Frontend para Vercel

### Estrutura de Pastas

```
facial-manager/
├── frontend/              (create this)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── app/                   (API — já existente)
└── requirements.txt
```

### Criar Frontend (se ainda não existe)

Se precisar criar um frontend React/Vite novo:

```bash
# 1. Criar novo projeto
npm create vite@latest frontend -- --template react-ts

# 2. Instalar dependências
cd frontend
npm install axios react-router-dom @tanstack/react-query

# 3. Configurar .env
echo "VITE_API_URL=https://pontix-api.onrender.com" > .env
echo "VITE_API_URL=http://localhost:8000" > .env.development
```

### Arquivo `.env.example` (frontend)

```env
# .env.example (frontend)
VITE_API_URL=https://pontix-api.onrender.com
VITE_APP_NAME=Pontix - Portal do Contador
VITE_LOG_LEVEL=info
```

---

## Part 3: Deploy Frontend no Vercel

### Passo 1: Conectar ao Vercel

1. Acesse [https://vercel.com](https://vercel.com)
2. Clique em **"Add New..." → "Project"**
3. Importe o repositório GitHub
4. Selecione `Gerenciador_de_ponto` (ou `Pontix_`)

### Passo 2: Configurar Build

No Vercel, configure:

```
Framework: Vite
Build Command: npm run build (na pasta frontend)
Output Directory: frontend/dist
Node Version: 18.x ou 20.x
```

### Passo 3: Variáveis de Ambiente (Vercel)

```
VITE_API_URL = https://pontix-api.onrender.com
VITE_APP_NAME = Pontix - Portal do Contador
```

### Passo 4: Deploy

1. Clique em **"Deploy"**
2. Vercel construirá e deployará automaticamente
3. Frontend estará disponível em `https://pontix.vercel.app` (ou seu domínio customizado)

### Configurar Domínio Customizado (Vercel)

1. Vercel Dashboard → Project Settings → Domains
2. Adicionar domínio próprio
3. Configurar DNS (Vercel fornece instruções)

---

## Part 4: Verificação Pós-Deploy

### Checklist API (Render)

- [ ] Health check retorna `200 OK`
- [ ] Swagger docs acessível
- [ ] Autenticação funciona (JWT)
- [ ] Banco de dados conectado
- [ ] CORS configurado para frontend

### Checklist Frontend (Vercel)

- [ ] Página carrega sem erros
- [ ] API calls funcionam
- [ ] Login/logout funciona
- [ ] Tabelas de ocorrências carregam
- [ ] Filtros funcionam

### Teste de API

```bash
# 1. Health check
curl https://pontix-api.onrender.com/health

# 2. Docs
curl https://pontix-api.onrender.com/docs

# 3. Autenticação
curl -X POST https://pontix-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}'

# 4. Listar empresas (com token)
curl https://pontix-api.onrender.com/api/v1/accountant/companies \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Part 5: CI/CD Setup

### GitHub Actions (automático com Render + Vercel)

Quando você fizer push para `master`:

1. **Render**: Deploy automático da API (configurado via `render.yaml`)
2. **Vercel**: Deploy automático do frontend (via GitHub integration)

### Monitorar Deployments

**Render Dashboard**
- Services → pontix-api → Logs

**Vercel Dashboard**
- Deployments → Ver status

---

## Part 6: Configuração Pós-Deploy

### Supabase Setup (Cloud Database)

1. Acesse [https://supabase.com](https://supabase.com)
2. Crie um novo projeto
3. Configure variáveis no Render:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

### Configurar CORS (Render API)

Em `app/main.py`, adicione:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pontix.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Configurar Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## Part 7: Monitoramento e Logs

### Render Logs

```bash
# Ver últimos logs
curl https://api.render.com/v1/services/YOUR_SERVICE_ID/logs \
  -H "Authorization: Bearer YOUR_RENDER_API_KEY"
```

### Vercel Analytics

- Dashboard → Analytics
- View count, Performance, etc.

### Sentry (Error Tracking)

```python
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

---

## Part 8: Troubleshooting

### Erro: "502 Bad Gateway"

- Verificar logs no Render Dashboard
- Confirmar variáveis de ambiente estão corretas
- Reiniciar serviço

### Erro: "CORS policy"

- Adicionar origem do frontend em `CORS_ORIGINS`
- Redeploy API

### Erro: "Database connection"

- Verificar `DATABASE_URL` / `SUPABASE_URL`
- Testar conexão localmente

### Erro: "Module not found"

- Verificar `requirements.txt` está atualizado
- Rodar `pip install -r requirements.txt` localmente

---

## Part 9: URLs de Produção

| Serviço | URL | Documentação |
|---------|-----|--------------|
| **API** | https://pontix-api.onrender.com | /docs |
| **Frontend** | https://pontix.vercel.app | / |
| **Docs** | https://pontix-api.onrender.com/docs | API |
| **OpenAPI** | https://pontix-api.onrender.com/openapi.json | Schema |
| **Health** | https://pontix-api.onrender.com/health | Status |

---

## Part 10: Updates e Manutenção

### Atualizar Código

```bash
# 1. Fazer mudanças localmente
# 2. Commit e push
git add .
git commit -m "feat: nova funcionalidade"
git push origin master

# 3. Render e Vercel deployam automaticamente
# 4. Monitorar no Dashboard
```

### Rollback

- **Render**: Deployments → Selecionar versão anterior → "Redeploy"
- **Vercel**: Deployments → Selecionar versão anterior → "Promote to Production"

### Atualizações de Dependências

```bash
# Atualizar requirements
pip list --outdated
pip install --upgrade package-name
pip freeze > requirements.txt
git add requirements.txt
git commit -m "chore: atualizar dependências"
git push origin master
```

---

## Conclusão

Sua aplicação Pontix agora está live em produção! 🚀

- **API**: https://pontix-api.onrender.com
- **Frontend**: https://pontix.vercel.app
- **Documentação**: https://pontix-api.onrender.com/docs

Para suporte, consulte:
- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
