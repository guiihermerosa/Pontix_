# Guia de Deploy do Pontix

## Arquitetura de Produção

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   SISTEMA LOCAL │     │      RENDER     │     │     VERCEL     │
│   (Python)      │────▶│   (FastAPI)     │◀───▶│    (React)     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    SUPABASE     │
                        │  (PostgreSQL)   │
                        │   (Auth)        │
                        │   (Storage)     │
                        └─────────────────┘
```

## 1. Configuração do Supabase

### 1.1 Criar projeto no Supabase
1. Acesse [supabase.com](https://supabase.com)
2. Crie um novo projeto
3. Anote as credenciais:
   - `SUPABASE_URL` (ex: `https://xyz.supabase.co`)
   - `SUPABASE_KEY` (chave anônima/public)
   - `SUPABASE_SERVICE_KEY` (chave service role)

### 1.2 Configurar Banco de Dados
1. No SQL Editor do Supabase, execute o schema completo:
   ```sql
   -- Copie e execute o schema de app/database/models_supabase.py
   -- Ou use o arquivo schema.sql gerado
   ```

2. Configurar Row Level Security (RLS):
   ```sql
   -- As políticas RLS estão definidas no schema
   -- Verifique se estão ativadas
   ```

### 1.3 Configurar Authentication
1. Em Authentication → Settings:
   - Ativar "Confirm email"
   - Configurar "Site URL" com a URL do seu frontend
   - Configurar redirect URLs

## 2. Deploy no Render (API)

### 2.1 Método 1: Via Blueprint (Recomendado)
1. Conecte seu repositório GitHub no Render
2. Render detectará automaticamente o `render.yaml`
3. Configure as variáveis de ambiente:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` 
   - `SUPABASE_SERVICE_KEY`
   - `RESEND_API_KEY` (para emails)
   - `JWT_SECRET_KEY` (gerado automaticamente)

### 2.2 Método 2: Manual
1. Crie novo Web Service no Render
2. Configurações:
   - **Runtime**: Python 3.11+
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

3. Variáveis de ambiente obrigatórias:
   ```bash
   DEBUG=false
   SUPABASE_URL=https://seu-projeto.supabase.co
   SUPABASE_KEY=sua-chave-anon
   SUPABASE_SERVICE_KEY=sua-chave-service
   JWT_SECRET_KEY=chave-aleatoria-longa
   RESEND_API_KEY=re_xxx
   CORS_ORIGINS=https://seu-frontend.vercel.app
   ```

## 3. Deploy no Vercel (Frontend React)

### 3.1 Preparar projeto React
1. Estrutura básica do frontend:
   ```
   pontix-frontend/
   ├── public/
   ├── src/
   │   ├── components/
   │   ├── pages/
   │   │   ├── Dashboard/
   │   │   ├── Auth/
   │   │   └── Portal/
   │   ├── services/
   │   ├── hooks/
   │   └── utils/
   ├── package.json
   └── vercel.json
   ```

2. Configurar `vercel.json`:
   ```json
   {
     "buildCommand": "npm run build",
     "devCommand": "npm run dev",
     "installCommand": "npm install",
     "outputDirectory": "dist",
     "framework": "react",
     "env": {
       "VITE_API_URL": "https://pontix-api.onrender.com",
       "VITE_SUPABASE_URL": "https://seu-projeto.supabase.co",
       "VITE_SUPABASE_KEY": "sua-chave-anon"
     }
   }
   ```

### 3.2 Variáveis de ambiente no Vercel
```bash
VITE_API_URL=https://sua-api.onrender.com
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_KEY=sua-chave-anon-public
VITE_APP_NAME=Pontix
```

## 4. Sistema Local (Empresas)

### 4.1 Instalação
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/pontix.git
cd pontix

# Instale dependências
pip install -r requirements.txt

# Configure variáveis locais
cp .env.example .env
# Edite .env com configurações locais

# Inicie o sistema
python run.py
```

### 4.2 Configuração local
No arquivo `.env` local:
```bash
# Modo local
DEBUG=true
DATABASE_URL=sqlite:///./data/facial.db

# Conexão com nuvem (para sincronização)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon

# Configurações da empresa local
COMPANY_NAME=Nome da Empresa
COMPANY_CNPJ=XX.XXX.XXX/XXXX-XX
```

## 5. Configuração de Email (Resend)

### 5.1 Criar conta no Resend
1. Acesse [resend.com](https://resend.com)
2. Crie uma API Key
3. Verifique um domínio para envio

### 5.2 Configurar no Render/Vercel
```bash
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=contato@seu-dominio.com
RESEND_FROM_NAME=Pontix
```

## 6. Monitoramento e Manutenção

### 6.1 Logs
- **Render**: Dashboard → Logs
- **Vercel**: Analytics → Logs
- **Supabase**: Logs Explorer

### 6.2 Backups
- **Supabase**: Backup automático diário
- **Render**: Configurar backup do banco
- **Local**: Script de backup automático

### 6.3 Monitoramento de Saúde
```bash
# Endpoints de health check
GET https://pontix-api.onrender.com/health
GET https://pontix-api.onrender.com/auth/health
GET https://pontix-api.onrender.com/portal/health
```

## 7. Troubleshooting

### 7.1 Erros comuns
1. **CORS errors**: Verifique `CORS_ORIGINS` no Render
2. **Auth errors**: Verifique tokens JWT e Supabase keys
3. **Database errors**: Verifique conexão com Supabase
4. **Sync errors**: Verifique internet e credenciais

### 7.2 Logs importantes
```bash
# Logs da aplicação
logs/pontix.log

# Logs de sincronização
app/services/sync_service.py

# Logs de autenticação
app/auth/auth_service.py
```

## 8. Escalabilidade

### 8.1 Render
- Upgrade para plano `standard` para mais recursos
- Configurar auto-scaling
- Usar Redis para cache (opcional)

### 8.2 Supabase
- Monitorar uso de banco
- Considerar upgrade para plano superior
- Otimizar queries com índices

### 8.3 Vercel
- Usar Edge Functions para performance
- Configurar CDN para assets estáticos
- Monitorar limite de funções serverless

## 9. Segurança

### 9.1 Boas práticas
1. **Nunca** commitar `.env` ou credenciais
2. Usar variáveis de ambiente em produção
3. Rotacionar chaves periodicamente
4. Usar HTTPS em todas as conexões
5. Implementar rate limiting na API

### 9.2 Auditoria
- Revisar logs de auditoria regularmente
- Monitorar tentativas de acesso não autorizado
- Manter logs por pelo menos 90 dias

## 10. Atualizações

### 10.1 Atualizar API
```bash
# Render faz deploy automático do GitHub
# Ou manualmente via dashboard
```

### 10.2 Atualizar Frontend
```bash
# Vercel faz deploy automático
# Ou via vercel cli:
vercel --prod
```

### 10.3 Atualizar Sistema Local
```bash
git pull origin main
pip install -r requirements.txt
# Reiniciar serviço
```

---

## Links úteis
- [Documentação Render](https://render.com/docs)
- [Documentação Vercel](https://vercel.com/docs)
- [Documentação Supabase](https://supabase.com/docs)
- [Documentação Resend](https://resend.com/docs)