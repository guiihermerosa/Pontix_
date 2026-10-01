# 🚀 Guia de Deployment - Pontix Cloud

Este guia detalha o processo de deploy do Pontix Cloud para produção usando Render (backend) e Vercel (frontend).

---

## 📋 Pré-requisitos

- [ ] Conta no GitHub (repositório público ou privado)
- [ ] Conta no [Render](https://render.com) (para backend)
- [ ] Conta no [Vercel](https://vercel.com) (para frontend)
- [ ] Conta no [Supabase](https://supabase.com) (para banco de dados)
- [ ] Conta no [Resend](https://resend.com) (para emails - opcional)

---

## 1️⃣ Preparar Supabase

### Criar Projeto Supabase

1. Acesse https://supabase.com e faça login
2. Clique em "New Project"
3. Preencha:
   - **Name**: `pontix-cloud`
   - **Database Password**: Gere uma senha forte
   - **Region**: Escolha a mais próxima (ex: South America - São Paulo)
4. Aguarde a criação (5-10 minutos)

### Obter Credenciais

Na dashboard do projeto, clique em "Settings" → "API":

1. **Project URL** (SUPABASE_URL):
   ```
   https://seu-projeto.supabase.co
   ```

2. **Anon Public Key** (SUPABASE_KEY):
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Service Role Key** (SUPABASE_SERVICE_KEY):
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

Salve essas informações - você precisará delas.

### Executar Migrações

Se planeja usar Supabase em produção:

1. Clone o repositório localmente
2. Configure o .env com credenciais Supabase
3. Execute:
   ```bash
   cd backend
   python migrations.py create
   ```

---

## 2️⃣ Deploy Backend - Render

### Passo 1: Conectar GitHub

1. Acesse https://render.com e faça login
2. Clique em "New" → "Web Service"
3. Clique em "Connect a Repository"
4. Autorize Render a acessar seu GitHub
5. Selecione o repositório `facial-manager-cloud`

### Passo 2: Configurar Serviço Web

1. **Name**: `pontix-cloud-api`
2. **Environment**: `Python 3`
3. **Region**: `São Paulo` (ou próximo)
4. **Branch**: `main` (ou sua branch de produção)
5. **Build Command**:
   ```
   pip install -r requirements.txt && python migrations.py create
   ```
6. **Start Command**:
   ```
   python run.py
   ```
7. **Instance Type**: `Starter` (para começar)

### Passo 3: Configurar Variáveis de Ambiente

Clique em "Environment" e adicione:

```env
DEBUG=False
REQUIRE_AUTH=True
APP_URL=https://pontix-cloud-api.onrender.com
WEB_APP_URL=https://pontix-cloud.vercel.app

SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-publica
SUPABASE_SERVICE_KEY=sua-chave-service-role

JWT_SECRET_KEY=gere-uma-chave-super-secreta-e-aleatoria-123xyz!@#
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

RESEND_API_KEY=re_sua_chave_do_resend
RESEND_FROM_EMAIL=noreply@pontix.com
RESEND_FROM_NAME=Pontix Cloud

CORS_ORIGINS=https://pontix-cloud.vercel.app,https://localhost:3000,http://localhost:5173
ALLOWED_HOSTS=pontix-cloud-api.onrender.com,localhost

LOG_LEVEL=INFO
```

### Passo 4: Deploy

1. Clique em "Create Web Service"
2. Aguarde o deploy (5-10 minutos)
3. Acesse a URL fornecida (ex: https://pontix-cloud-api.onrender.com)
4. Teste o health check: https://pontix-cloud-api.onrender.com/health

---

## 3️⃣ Deploy Frontend - Vercel

### Passo 1: Conectar GitHub

1. Acesse https://vercel.com e faça login
2. Clique em "Add New..." → "Project"
3. Procure por `facial-manager-cloud`
4. Clique "Import"

### Passo 2: Configurar Projeto

1. **Framework Preset**: `Vue.js`
2. **Root Directory**: `frontend`
3. **Build and Output Settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`

### Passo 3: Configurar Variáveis de Ambiente

Clique em "Environment Variables" e adicione:

```env
VITE_API_URL=https://pontix-cloud-api.onrender.com
VITE_APP_NAME=Pontix Cloud
```

### Passo 4: Deploy

1. Clique em "Deploy"
2. Aguarde o deployment (2-5 minutos)
3. Acesse a URL fornecida (ex: https://pontix-cloud.vercel.app)

---

## 4️⃣ Testes Pós-Deploy

### Testar Backend

```bash
# Health check
curl https://pontix-cloud-api.onrender.com/health

# Documentação da API
curl https://pontix-cloud-api.onrender.com/docs

# Tentar login (esperado 401 ou sucesso com credenciais corretas)
curl -X POST https://pontix-cloud-api.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

### Testar Frontend

1. Acesse https://pontix-cloud.vercel.app
2. Você deve ver a página com navigation
3. Tente clicar em "Contador" e "Proprietário"
4. Verifique que os dados são carregados (ou mostram erro de conexão se sem token)

### Testar Sincronização

```bash
# Sincronizar funcionários de teste
curl -X POST https://pontix-cloud-api.onrender.com/api/sync/employees \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "test-company-id",
    "company_data": {"name": "Test", "cnpj": "12.345.678/0001-00"},
    "employees": [
      {"local_id": "1", "user_id": "001", "full_name": "Employee 1"}
    ]
  }'
```

---

## 🔧 Configuração Pós-Deploy

### Email com Resend

1. Crie conta em https://resend.com
2. Verifique seu domínio (recomendado)
3. Gere API Key
4. Adicione a chave na variável `RESEND_API_KEY`

### Domínio Personalizado (Opcional)

#### Render (Backend)

1. Na dashboard do serviço, clique "Settings"
2. Vá para "Custom Domain"
3. Adicione seu domínio (ex: `api.pontix.com.br`)
4. Siga as instruções para atualizar DNS

#### Vercel (Frontend)

1. Na dashboard do projeto, clique "Settings"
2. Vá para "Domains"
3. Adicione seu domínio (ex: `pontix.com.br`)
4. Verifique DNS

---

## 📊 Monitoramento

### Logs - Render

1. Na dashboard do serviço, clique "Logs"
2. Você verá logs em tempo real
3. Procure por erros ou avisos

### Logs - Vercel

1. Na dashboard do projeto, clique "Analytics"
2. Veja requisições, erros e performance

### Alertas - Ambos

Ambas as plataformas permitem configurar alertas para:
- Falhas de build
- Latência alta
- Taxa de erro elevada

---

## 🔄 Updates e Rollbacks

### Update Automático

- Quando você faz push para `main`:
  - Render faz rebuild e deploy automático
  - Vercel faz build e deploy automático
- O deploy anterior fica disponível para rollback

### Rollback Manual

#### Render
1. Na dashboard, clique "Deploys"
2. Selecione um deploy anterior
3. Clique "Redeploy"

#### Vercel
1. Na dashboard, clique "Deployments"
2. Encontre um anterior
3. Clique "Promote to Production"

---

## 🐛 Troubleshooting

### Backend não conecta ao Supabase

**Erro**: `sqlalchemy.exc.OperationalError`

**Solução**:
1. Verifique SUPABASE_URL (deve ter https://)
2. Verifique SUPABASE_KEY (não vazia)
3. Teste conexão localmente com mesmas credenciais
4. Verifique firewall/rede do Supabase

### Frontend não conecta ao Backend

**Erro**: `CORS error` ou `Cannot reach server`

**Solução**:
1. Verifique VITE_API_URL está correto
2. Verifique CORS_ORIGINS no backend inclui o URL do frontend
3. Backend está rodando? Tente acessar /health
4. Aguarde alguns segundos (Render tem cold start)

### Build falha

**Erro**: `requirements.txt not found` ou `npm not found`

**Solução**:
1. Verifique "Root Directory" ou caminho correto
2. Verifique requirements.txt/package.json existem
3. Confira build command está correto

### Database seed falha

**Erro**: `python migrations.py create` fails

**Solução**:
1. Tente rodar localmente para debug
2. Verifique SUPABASE_SERVICE_KEY tem permissões
3. Reduza número de registros seed

---

## 📈 Scaling para Produção

### Performance - Backend (Render)

Para mais requisições:
1. Upgrade para "Standard" ou "Pro"
2. Aumente workers/threads em uvicorn
3. Ative caching com Redis (adicione no render.yaml)

### Performance - Frontend (Vercel)

Vercel escala automaticamente via CDN. Para otimizar:
1. Comprime imagens
2. Lazy load componentes
3. Ative Service Workers para offline

### Database - Supabase

Supabase auto-escala. Para performance:
1. Ative backup automático
2. Configure índices nas tabelas
3. Monitore conexões e queries

---

## 🔐 Segurança Pós-Deploy

### Checklist de Segurança

- [ ] DEBUG=False em produção
- [ ] REQUIRE_AUTH=True
- [ ] JWT_SECRET_KEY é único e forte (>32 caracteres)
- [ ] CORS_ORIGINS não inclui `*`
- [ ] Senhas Supabase são fortes
- [ ] Chaves API (Resend, etc) estão seguras
- [ ] HTTPS habilitado (automático em Render/Vercel)
- [ ] Backup automático do Supabase configurado

### Rotação de Secrets

A cada 90 dias:
1. Gere nova JWT_SECRET_KEY
2. Gere novos tokens Supabase
3. Gere nova chave Resend
4. Atualize em Render/Vercel

---

## 📞 Suporte

### Documentação Oficial

- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [Supabase Docs](https://supabase.com/docs)

### Comunidades

- [Render Community](https://discord.gg/render)
- [Vercel Community](https://discord.gg/vercel)
- [Supabase Community](https://discord.gg/supabase)

---

## ✅ Checklist Final

- [ ] Supabase projeto criado
- [ ] Credenciais Supabase obtidas
- [ ] Backend deploado em Render
- [ ] Frontend deploado em Vercel
- [ ] Variáveis de ambiente configuradas
- [ ] Health check funciona
- [ ] Testes básicos passam
- [ ] Logs sem erros
- [ ] Domínios personalizados (opcional)
- [ ] Backups configurados
- [ ] Monitoramento ativado

---

Parabéns! 🎉 Pontix Cloud está em produção!

