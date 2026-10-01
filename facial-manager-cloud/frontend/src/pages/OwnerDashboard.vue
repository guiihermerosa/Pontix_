<template>
  <div class="owner-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1>Painel do Proprietário</h1>
        <p class="header-subtitle">Visão geral de todas as suas empresas e integrações</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>Carregando dados...</p>
    </div>

    <!-- Error State -->
    <div v-if="error && !loading" class="error-banner">
      <span class="error-icon">⚠️</span>
      <span>{{ error }}</span>
    </div>

    <!-- Main Content -->
    <div v-if="!loading && !error" class="dashboard-content">
      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">🏢</div>
          <div class="stat-info">
            <p class="stat-label">Empresas</p>
            <p class="stat-value">{{ stats.total_companies }}</p>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">👥</div>
          <div class="stat-info">
            <p class="stat-label">Total de Funcionários</p>
            <p class="stat-value">{{ stats.total_employees }}</p>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⏱️</div>
          <div class="stat-info">
            <p class="stat-label">Registros de Ponto</p>
            <p class="stat-value">{{ stats.total_time_records }}</p>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📋</div>
          <div class="stat-info">
            <p class="stat-label">Ocorrências Pendentes</p>
            <p class="stat-value">{{ stats.pending_occurrences }}</p>
          </div>
        </div>
      </div>

      <!-- Companies Section -->
      <section class="section">
        <div class="section-header">
          <div>
            <h2>Empresas Conectadas</h2>
            <p class="section-subtitle">Gerencie suas empresas conectadas ao Pontix Cloud</p>
          </div>
        </div>

        <!-- Search & Filter -->
        <div class="search-filter-bar">
          <input
            v-model="searchCompanies"
            type="text"
            placeholder="🔍 Buscar por nome, CNPJ ou email..."
            class="search-input"
          />
          <select v-model="filterStatus" class="filter-select">
            <option value="">Todos os status</option>
            <option value="active">Ativas</option>
            <option value="inactive">Inativas</option>
          </select>
        </div>

        <!-- Loading State -->
        <div v-if="companiesLoading" class="loading-container-sm">
          <div class="spinner-sm"></div>
          <p>Carregando empresas...</p>
        </div>

        <!-- Error State -->
        <div v-if="companiesError && !companiesLoading" class="error-banner-sm">
          <span class="error-icon">⚠️</span>
          <span>{{ companiesError }}</span>
        </div>

        <!-- Companies Grid -->
        <div v-if="!companiesLoading && !companiesError" class="companies-grid">
          <div
            v-for="company in filteredCompanies"
            :key="company.id"
            class="company-card"
          >
            <div class="card-header">
              <h3>{{ company.name }}</h3>
              <span :class="['status-badge', company.is_active ? 'active' : 'inactive']">
                {{ company.is_active ? '✓ Ativa' : '✗ Inativa' }}
              </span>
            </div>
            <div class="card-body">
              <div class="card-row">
                <span class="label">CNPJ:</span>
                <span class="value">{{ company.cnpj || '-' }}</span>
              </div>
              <div class="card-row">
                <span class="label">Email:</span>
                <span class="value">{{ company.email || '-' }}</span>
              </div>
              <div class="card-row">
                <span class="label">Data de Criação:</span>
                <span class="value">{{ formatDate(company.created_at) }}</span>
              </div>
            </div>
            <div class="card-footer">
              <button class="btn-primary" @click="editCompany(company)">
                ✏️ Editar
              </button>
              <button class="btn-secondary" @click="viewDetails(company)">
                👁️ Detalhes
              </button>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="filteredCompanies.length === 0" class="empty-state">
            <div class="empty-icon">🏢</div>
            <p class="empty-title">Nenhuma empresa encontrada</p>
            <p class="empty-text">
              {{ searchCompanies || filterStatus ? 'Tente ajustar seus filtros' : 'Nenhuma empresa conectada ainda' }}
            </p>
          </div>
        </div>
      </section>

      <!-- Integrations Section -->
      <section class="section">
        <div class="section-header">
          <div>
            <h2>Integrações</h2>
            <p class="section-subtitle">Configure suas integrações para melhor funcionamento do Pontix Cloud</p>
          </div>
        </div>

        <div class="integrations-grid">
          <div class="integration-card">
            <div class="integration-icon">📧</div>
            <h3>Email (Resend)</h3>
            <p class="integration-description">Notificações de ocorrências e alertas</p>
            <div :class="['integration-status', integrations.resend ? 'active' : 'inactive']">
              {{ integrations.resend ? '✓ Configurado' : '✗ Não configurado' }}
            </div>
            <button
              :class="['btn-integration', integrations.resend ? 'danger' : 'primary']"
              @click="showSettings()"
            >
              {{ integrations.resend ? '⚙️ Reconfigurar' : '⚙️ Configurar' }}
            </button>
          </div>

          <div class="integration-card">
            <div class="integration-icon">☁️</div>
            <h3>Sincronização em Nuvem</h3>
            <p class="integration-description">Sincronize dados em tempo real</p>
            <div :class="['integration-status', integrations.cloudSync ? 'active' : 'inactive']">
              {{ integrations.cloudSync ? '✓ Ativo' : '✗ Inativo' }}
            </div>
            <button
              :class="['btn-integration', integrations.cloudSync ? 'secondary' : 'primary']"
              @click="toggleCloudSync()"
            >
              {{ integrations.cloudSync ? '🔴 Desativar' : '🟢 Ativar' }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { api } from '@/services/api'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default {
  name: 'OwnerDashboard',
  data() {
    return {
      loading: true,
      error: null,
      companiesLoading: false,
      companiesError: null,
      searchCompanies: '',
      filterStatus: '',
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
    },
    filteredCompanies() {
      let filtered = this.companies.items

      // Filter by search term
      if (this.searchCompanies.trim()) {
        const term = this.searchCompanies.toLowerCase()
        filtered = filtered.filter(company =>
          company.name.toLowerCase().includes(term) ||
          (company.cnpj && company.cnpj.includes(term)) ||
          (company.email && company.email.toLowerCase().includes(term))
        )
      }

      // Filter by status
      if (this.filterStatus) {
        const isActive = this.filterStatus === 'active'
        filtered = filtered.filter(company => company.is_active === isActive)
      }

      return filtered
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
        const response = await api.get('/owner/companies?page=1&page_size=100', {
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
        return format(new Date(dateString), 'dd/MM/yyyy', { locale: ptBR })
      } catch {
        return dateString
      }
    },
    
    editCompany(company) {
      console.log('Editar empresa:', company)
      // TODO: Abrir modal de edição
    },
    
    viewDetails(company) {
      console.log('Ver detalhes da empresa:', company)
      // TODO: Navegar para página de detalhes da empresa
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
  min-height: 100vh;
  background-color: #f8f9fa;
}

/* Header */
.dashboard-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 700;
}

.header-subtitle {
  margin: 0;
  font-size: 1rem;
  opacity: 0.95;
  font-weight: 300;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem 2rem 1rem;
}

/* Loading State */
.loading-container,
.loading-container-sm {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem 1rem;
  color: #666;
}

.loading-container-sm {
  padding: 1.5rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f0f0f0;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-sm {
  width: 24px;
  height: 24px;
  border: 3px solid #f0f0f0;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Error Banner */
.error-banner,
.error-banner-sm {
  background-color: #fee;
  border-left: 4px solid #dc2626;
  color: #991b1b;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.error-banner-sm {
  margin-bottom: 1rem;
  padding: 0.75rem;
  font-size: 0.9rem;
}

.error-icon {
  font-size: 1.2rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  gap: 1rem;
  border: 1px solid #e5e7eb;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  font-size: 2.5rem;
  min-width: 50px;
  text-align: center;
}

.stat-info {
  flex: 1;
}

.stat-label {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  margin: 0.5rem 0 0 0;
  font-size: 2rem;
  font-weight: 700;
  color: #667eea;
}

/* Sections */
.section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
  border: 1px solid #e5e7eb;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #f0f0f0;
}

.section-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.section-subtitle {
  margin: 0.25rem 0 0 0;
  font-size: 0.9rem;
  color: #666;
}

/* Search & Filter */
.search-filter-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.search-input,
.filter-select {
  flex: 1;
  min-width: 200px;
  padding: 0.75rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: inherit;
  transition: border-color 0.2s;
}

.search-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* Companies Grid */
.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.company-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
}

.company-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  border-color: #667eea;
}

.card-header {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1f2937;
}

.status-badge {
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge.active {
  background-color: #dcfce7;
  color: #166534;
}

.status-badge.inactive {
  background-color: #fee2e2;
  color: #991b1b;
}

.card-body {
  padding: 1rem;
}

.card-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.card-row:last-child {
  margin-bottom: 0;
}

.card-row .label {
  color: #666;
  font-weight: 500;
}

.card-row .value {
  color: #1f2937;
  font-family: 'Courier New', monospace;
}

.card-footer {
  padding: 1rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 0.75rem;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 0.6rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover {
  background-color: #5568d3;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background-color: #e5e7eb;
  color: #374151;
}

.btn-secondary:hover {
  background-color: #d1d5db;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #666;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
}

.empty-text {
  margin: 0;
  font-size: 0.95rem;
}

/* Integrations Grid */
.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.integration-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.3s;
}

.integration-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #667eea;
}

.integration-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.integration-card h3 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
}

.integration-description {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #666;
}

.integration-status {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.integration-status.active {
  background-color: #dcfce7;
  color: #166534;
}

.integration-status.inactive {
  background-color: #fee2e2;
  color: #991b1b;
}

.btn-integration {
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-integration.primary {
  background-color: #667eea;
  color: white;
}

.btn-integration.primary:hover {
  background-color: #5568d3;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-integration.secondary {
  background-color: #e5e7eb;
  color: #374151;
}

.btn-integration.secondary:hover {
  background-color: #d1d5db;
}

.btn-integration.danger {
  background-color: #fecaca;
  color: #7f1d1d;
}

.btn-integration.danger:hover {
  background-color: #fca5a5;
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-header {
    padding: 1.5rem 1rem;
  }

  .dashboard-header h1 {
    font-size: 1.5rem;
  }

  .header-subtitle {
    font-size: 0.9rem;
  }

  .dashboard-content {
    padding: 0 1rem 1.5rem 1rem;
  }

  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  .stat-card {
    padding: 1rem;
  }

  .stat-icon {
    font-size: 1.75rem;
    min-width: 40px;
  }

  .stat-label {
    font-size: 0.75rem;
  }

  .stat-value {
    font-size: 1.5rem;
  }

  .section {
    padding: 1.5rem 1rem;
    margin-bottom: 1.5rem;
  }

  .section-header {
    flex-direction: column;
    gap: 0.5rem;
  }

  .section-header h2 {
    font-size: 1.2rem;
  }

  .search-filter-bar {
    flex-direction: column;
    gap: 0.75rem;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .companies-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .card-footer {
    flex-direction: column;
  }

  .integrations-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .card-row {
    flex-direction: column;
    gap: 0.25rem;
  }

  .card-row .label {
    font-weight: 600;
  }
}

@media (max-width: 480px) {
  .dashboard-header h1 {
    font-size: 1.25rem;
  }

  .dashboard-content {
    padding: 0 0.75rem 1rem 0.75rem;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-card {
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .section {
    padding: 1rem;
  }

  .stat-icon {
    font-size: 1.5rem;
  }

  .stat-value {
    font-size: 1.25rem;
  }

  .stat-label {
    font-size: 0.65rem;
  }
}
</style>
