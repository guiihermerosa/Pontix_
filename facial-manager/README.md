# Pontix

Sistema local de gerenciamento do dispositivo biométrico **ALTEK ALPHA-1111**.

Funciona como camada intermediária entre o usuário e o Web Service embarcado do equipamento, com sincronização automática, dashboard, gerenciamento de funcionários, presença, logs e exportação.

---

## Requisitos

- Python 3.12+
- Rede local com acesso ao IP do facial
- Windows / Linux / macOS

---

## 1. Instalação

```bash
# Clone ou copie a pasta pontix para o servidor local
cd pontix

# Instale as dependências
pip install -r requirements.txt
```

---

## 2. Execução

```bash
# Opção A — script direto
python run.py

# Opção B — uvicorn manual
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

O sistema estará disponível em: **http://localhost:8000**

---

## 3. Configuração inicial

1. Acesse **http://localhost:8000**
2. Vá em **Configurações → Sistema**
3. Preencha:
   - **IP do Dispositivo** — ex.: `192.168.0.24`
   - **Porta** — padrão `80`
   - **Senha** — senha de admin do ALPHA-1111
4. Clique em **Testar Conexão** para validar
5. Salve as configurações

A senha é armazenada no banco SQLite local e **nunca** é exibida na interface após ser definida.

---

## 4. Banco de dados

O banco é criado automaticamente em `data/facial.db` na primeira execução.

Não é necessário rodar nenhum script de migração.

Para resetar o banco (apaga todos os dados):

```bash
# Windows
del data\facial.db

# Linux/macOS
rm data/facial.db
```

Na próxima execução o banco é recriado com as configurações padrão.

---

## 5. Configuração do IP do facial

No painel **Configurações → Sistema**, informe o IP do dispositivo conforme configurado na rede local.

Para descobrir o IP do facial:
- Acesse a interface web do equipamento diretamente pelo navegador
- Consulte o roteador da rede
- Ou use a rota `POST /IpSetting` conforme documentado em `docs/FACIAL_API.md`

---

## 6. Teste de conexão

**Configurações → Sistema → Testar Conexão**

O sistema executa `POST /getDevAuth` no dispositivo e exibe:
- Status online/offline
- Tempo de resposta em ms
- Mensagem de erro em caso de falha

---

## 7. Sincronização

### Automática

O serviço de sincronização inicia junto com a aplicação.

Configurável em **Configurações → Sincronização**:
- Intervalo: 2s / 5s / 10s / 30s / 60s / 5min
- Ativar/desativar por tipo (funcionários / marcações)

### Manual

- Botão **Sincronizar** na barra superior (qualquer página)
- Botão **Sincronizar agora** em Configurações → Sincronização
- Botão **Importar do device** na página de Funcionários
- Botão **Buscar no device** na página de Presença

### Fila de sincronização

Toda operação (cadastro, edição de funcionário) é enfileirada na tabela `sync_queue`. Se o device estiver offline, a operação fica como `PENDING` e é reprocessada no próximo ciclo. Após 5 tentativas com erro, a operação fica como `ERROR` e pode ser visualizada em Relatórios → Fila de Sincronização.

---

## 8. Exportação

**Relatórios** → selecione o período e clique em **Exportar Excel** ou **Exportar CSV**.

Relatórios disponíveis:
- Presença (filtros: data, funcionário, tipo)
- Cadastro de funcionários

Arquivos Excel possuem formatação profissional com cabeçalho colorido, linhas alternadas e largura automática de colunas.

---

## 9. Estrutura do projeto

```
pontix/
│
├── app/
│   ├── main.py                  # Entrada FastAPI, lifespan, rotas
│   │
│   ├── api/
│   │   ├── routes_dashboard.py  # GET / e /api/dashboard
│   │   ├── routes_employees.py  # CRUD funcionários
│   │   ├── routes_attendance.py # Presença e polling
│   │   ├── routes_settings.py   # Configs do sistema e do device
│   │   └── routes_sync.py       # Controle de sincronização
│   │
│   ├── services/
│   │   ├── facial_client.py     # ÚNICA classe que fala com o device
│   │   ├── sync_service.py      # Loop de sincronização assíncrono
│   │   ├── employee_service.py  # Lógica de funcionários
│   │   ├── attendance_service.py# Polling e consultas de presença
│   │   └── export_service.py    # Geração de XLSX e CSV
│   │
│   ├── database/
│   │   ├── database.py          # Engine, sessão, init_db
│   │   └── models.py            # Tabelas SQLAlchemy
│   │
│   ├── schemas/
│   │   ├── employee.py
│   │   ├── attendance.py
│   │   └── settings.py
│   │
│   └── templates/               # Jinja2 HTML
│
├── static/
│   ├── css/app.css              # Design system completo
│   └── js/
│       ├── app.js               # Utilitários globais
│       ├── employees.js         # Lógica da página de funcionários
│       └── settings.js          # Lógica da página de configurações
│
├── data/
│   └── facial.db                # SQLite (criado automaticamente)
│
├── exports/                     # Arquivos gerados (opcional)
├── logs/
│   └── pontix.log       # Log rotativo
│
├── docs/
│   └── FACIAL_API.md            # Documentação das rotas do device
│
├── requirements.txt
├── run.py
└── README.md
```

---

## 10. Endpoints internos da aplicação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Dashboard principal |
| GET | `/funcionarios` | Página de funcionários |
| GET | `/presenca` | Página de presença |
| GET | `/relatorios` | Página de relatórios |
| GET | `/configuracoes` | Página de configurações |
| GET | `/api/dashboard` | Dados do dashboard (JSON) |
| GET | `/api/device/status` | Status do dispositivo |
| GET | `/api/employees` | Listar funcionários |
| POST | `/api/employees` | Criar funcionário |
| PUT | `/api/employees/{id}` | Atualizar funcionário |
| POST | `/api/employees/with-photo` | Criar com foto (multipart) |
| POST | `/api/employees/{id}/sync` | Sincronizar um funcionário |
| POST | `/api/employees/sync-all` | Importar todos do device |
| GET | `/api/attendance` | Listar marcações |
| GET | `/api/attendance/today` | Marcações de hoje |
| POST | `/api/attendance/poll` | Polling manual de presença |
| GET | `/api/sync` | Status da sincronização |
| POST | `/api/sync/run` | Executar ciclo agora |
| GET | `/api/sync/queue` | Fila de sincronização |
| GET | `/api/sync/logs` | Histórico de ciclos |
| GET | `/api/settings` | Ler configurações |
| PUT | `/api/settings` | Salvar configurações |
| POST | `/api/settings/test-connection` | Testar conexão com device |
| GET | `/api/reports/attendance.xlsx` | Exportar presença Excel |
| GET | `/api/reports/attendance.csv` | Exportar presença CSV |
| GET | `/api/reports/employees.xlsx` | Exportar funcionários Excel |
| GET | `/api/reports/employees.csv` | Exportar funcionários CSV |
| GET | `/api/logs` | Logs de comunicação |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

---

## Observações de segurança

- A senha do dispositivo é armazenada em texto no SQLite local. Em ambientes de produção, considere criptografar o valor com `cryptography.fernet`.
- O sistema é projetado para uso em **rede local** (LAN). Não exponha a porta 8000 para a internet sem autenticação adicional.
- Logs de comunicação nunca registram a senha nem dados biométricos completos.
