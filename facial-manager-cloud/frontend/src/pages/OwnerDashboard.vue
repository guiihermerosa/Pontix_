<template>
  <div class="owner-dashboard">
    <h2>Painel do Proprietário</h2>
    
    <div v-if="loading" class="loading">Carregando dados...</div>
    
    <div v-if="error" class="error-message">{{ error }}</div>
    
    <div v-if="!loading && !error" class="stats-grid">
      <div class="stat-card">
        <h3>Empresas</h3>
        <p class="stat-value">{{ stats.total_companies }}</p>
      </div>
      <div class="stat-card">
        <h3>Total de Funcionários</h3>
        <p class="stat-value">{{ stats.total_employees }}</p>
      </div>
      <div class="stat-card">
        <h3>Registros de Ponto</h3>
        <p class="stat-value">{{ stats.total_time_records }}</p>
      </div>
      <div class="stat-card">
        <h3>Ocorrências Pendentes</h3>
        <p class="stat-value">{{ stats.pending_occurrences }}</p>
      </div>
    </div>

    <div class="section">
      <h3>Empresas Conectadas</h3>
      <div v-if="companiesLoading" class="loading-sm">Carregando...</div>
      <div v-if="companiesError" class="error-message-sm">{{ companiesError }}</div>
      <div v-if="!companiesLoading && !companiesError" class="table-wrapper">
        <table class="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>CNPJ</th>
              <th>Email</th>
              <th>Status</th>
              <th>Data de Criação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="company in companies.items" :key="company.id">
              <td>{{ company.name }}</td>
              <td>{{ company.cnpj }}</td>
              <td>{{ company.email }}</td>
              <td :class="company.is_active ? 'active' : 'inactive'">
                {{ company.is_active ? 'Ativa' : 'Inativa' }}
              </td>
              <td>{{ formatDate(company.created_at) }}</td>
              <td>
                <button class="btn-sm" @click="editCompany(company)">Editar</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <h3>Integrações</h3>
      <p class="info-text">Configure suas integrações para melhor funcionamento do Pontix Cloud</p>
      <div class="integrations-grid">
        <div class="integration-card">
          <h4>Email (Resend)</h4>
          <p class="status-badge" :class="integrations.resend ? 'active' : 'inactive'">
            {{ integrations.resend ? '✓ Configurado' : '✗ Não configurado' }}
          </p>
          <button class="btn-sm" @click="showSettings()">Configurar</button>
        </div>
        <div class="integration-card">
          <h4>Sincronização em Nuvem</h4>
          <p class="status-badge" :class="integrations.cloudSync ? 'active' : 'inactive'">
            {{ integrations.cloudSync ? '✓ Ativo' : '✗ Inativo' }}
          </p>
          <button class="btn-sm" @click="toggleCloudSync()">{{ integrations.cloudSync ? 'Desativar' : 'Ativar' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '@/services/api'
import { formatISO, formatDate as fnsFormatDate } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default {
  name: 'OwnerDashboard',
  data() {
    return {
      loading: true,
      error: null,
      companiesLoading: false,
      companiesError: null,
      stats: {
        total_companies: 0,
        total_employees: 0,
        total_time_records: 0,
        pending_occurrences: 0,
      },
      companies: {
        items: [],
        total: 0,
        page: 1,
        pages: 0,
      },
      integrations: {
        resend: false,
        cloudSync: false
      }
    }
  },
  computed: {
    token() {
      return localStorage.getItem('access_token')
    }
  },
  mounted() {
    this.loadData()
  },
  methods: {
    async loadData() {
      this.loading = true
      this.error = null
      
      try {
        await Promise.all([
          this.loadDashboard(),
          this.loadCompanies()
        ])
      } catch (err) {
        this.error = 'Erro ao carregar dados: ' + (err.message || 'Erro desconhecido')
      } finally {
        this.loading = false
      }
    },
    
    async loadDashboard() {
      try {
        const response = await api.get('/owner/dashboard', {
          headers: this.getAuthHeaders()
        })
        this.stats = response.data.statistics
      } catch (err) {
        console.error('Erro ao carregar dashboard:', err)
        this.error = 'Erro ao carregar estatísticas'
      }
    },
    
    async loadCompanies() {
      this.companiesLoading = true
      this.companiesError = null
      
      try {
        const response = await api.get('/owner/companies?page=1&page_size=10', {
          headers: this.getAuthHeaders()
        })
        this.companies = response.data
      } catch (err) {
        console.error('Erro ao carregar empresas:', err)
        this.companiesError = 'Erro ao carregar empresas'
      } finally {
        this.companiesLoading = false
      }
    },
    
    getAuthHeaders() {
      return {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return '-'
      try {
        return fnsFormatDate(new Date(dateString), 'dd/MM/yyyy', { locale: ptBR })
      } catch {
        return dateString
      }
    },
    
    editCompany(company) {
      console.log('Editar empresa:', company)
      // TODO: Abrir modal de edição
    },
    
    showSettings() {
      console.log('Mostrar configurações')
      // TODO: Redirecionar para página de configurações
    },
    
    toggleCloudSync() {
      this.integrations.cloudSync = !this.integrations.cloudSync
      console.log('Cloud sync:', this.integrations.cloudSync)
      // TODO: Chamar API para atualizar configuração
    }
  }
}
</script>

<style scoped>
.owner-dashboard {
  padding: 1rem;
}

.loading, .loading-sm {
  text-align: center;
  padding: 2rem;
  color: #666;
  font-style: italic;
}

.loading-sm {
  padding: 1rem;
  font-size: 0.9rem;
}

.error-message {
  background-color: #fee;
  border: 1px solid #fcc;
  color: #c00;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.error-message-sm {
  background-color: #fee;
  border: 1px solid #fcc;
  color: #c00;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.info-text {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.stat-card h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.9;
}

.stat-value {
  margin: 0;
  font-size: 2rem;
  font-weight: bold;
}

.section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  margin-bottom: 1.5rem;
}

.section h3 {
  margin-top: 0;
}

.table-wrapper {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.table th {
  background-color: #f5f5f5;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #ddd;
}

.table td {
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.table tr:hover {
  background-color: #f9f9f9;
}

.active {
  color: #10b981;
  font-weight: 600;
}

.inactive {
  color: #ef4444;
  font-weight: 600;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.integration-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  background-color: #f9f9f9;
}

.integration-card h4 {
  margin: 0 0 0.5rem 0;
}

.status-badge {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 600;
}

.status-badge.active {
  color: #10b981;
}

.status-badge.inactive {
  color: #ef4444;
}

.btn-sm {
  padding: 0.4rem 0.8rem;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background-color 0.3s;
  margin-top: 0.5rem;
}

.btn-sm:hover {
  background-color: #5568d3;
}
</style>
