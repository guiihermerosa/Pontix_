<template>
  <div class="accounting-dashboard">
    <h2>Painel do Contador</h2>
    
    <div v-if="loading" class="loading">Carregando dados...</div>
    
    <div v-if="error" class="error-message">{{ error }}</div>
    
    <div v-if="!loading && !error" class="stats-grid">
      <div class="stat-card">
        <h3>Funcionários</h3>
        <p class="stat-value">{{ stats.total_employees }}</p>
      </div>
      <div class="stat-card">
        <h3>Registros Hoje</h3>
        <p class="stat-value">{{ stats.today_records }}</p>
      </div>
      <div class="stat-card">
        <h3>Ocorrências Pendentes</h3>
        <p class="stat-value">{{ stats.pending_occurrences }}</p>
      </div>
      <div class="stat-card">
        <h3>Justificativas Pendentes</h3>
        <p class="stat-value">{{ stats.pending_justifications }}</p>
      </div>
    </div>

    <div class="section">
      <h3>Funcionários</h3>
      <div v-if="employeesLoading" class="loading-sm">Carregando...</div>
      <div v-if="employeesError" class="error-message-sm">{{ employeesError }}</div>
      <div v-if="!employeesLoading && !employeesError" class="table-wrapper">
        <table class="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>CPF</th>
              <th>Departamento</th>
              <th>Cargo</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="emp in employees.items" :key="emp.id">
              <td>{{ emp.full_name }}</td>
              <td>{{ emp.cpf }}</td>
              <td>{{ emp.department }}</td>
              <td>{{ emp.role }}</td>
              <td>{{ emp.email }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <h3>Ocorrências</h3>
      <div v-if="occurrencesLoading" class="loading-sm">Carregando...</div>
      <div v-if="occurrencesError" class="error-message-sm">{{ occurrencesError }}</div>
      <div v-if="!occurrencesLoading && !occurrencesError" class="table-wrapper">
        <table class="table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Funcionário</th>
              <th>Tipo</th>
              <th>Severidade</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="occ in occurrences.items" :key="occ.id">
              <td>{{ formatDate(occ.occurrence_date) }}</td>
              <td>{{ occ.full_name }}</td>
              <td>{{ occ.occurrence_type }}</td>
              <td :class="occ.severity">{{ occ.severity }}</td>
              <td>{{ occ.status }}</td>
              <td>
                <button class="btn-sm" @click="showDetails(occ)">Detalhes</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '@/services/api'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default {
  name: 'AccountingDashboard',
  data() {
    return {
      loading: true,
      error: null,
      employeesLoading: false,
      employeesError: null,
      occurrencesLoading: false,
      occurrencesError: null,
      stats: {
        total_employees: 0,
        today_records: 0,
        pending_occurrences: 0,
        pending_justifications: 0,
      },
      employees: {
        items: [],
        total: 0,
        page: 1,
        pages: 0,
      },
      occurrences: {
        items: [],
        total: 0,
        page: 1,
        pages: 0,
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
          this.loadEmployees(),
          this.loadOccurrences()
        ])
      } catch (err) {
        this.error = 'Erro ao carregar dados: ' + (err.message || 'Erro desconhecido')
      } finally {
        this.loading = false
      }
    },
    
    async loadDashboard() {
      try {
        const response = await api.get('/accounting/dashboard', {
          headers: this.getAuthHeaders()
        })
        this.stats = response.data.statistics
      } catch (err) {
        console.error('Erro ao carregar dashboard:', err)
        this.error = 'Erro ao carregar estatísticas'
      }
    },
    
    async loadEmployees() {
      this.employeesLoading = true
      this.employeesError = null
      
      try {
        const response = await api.get('/accounting/employees?page=1&page_size=10', {
          headers: this.getAuthHeaders()
        })
        this.employees = response.data
      } catch (err) {
        console.error('Erro ao carregar funcionários:', err)
        this.employeesError = 'Erro ao carregar funcionários'
      } finally {
        this.employeesLoading = false
      }
    },
    
    async loadOccurrences() {
      this.occurrencesLoading = true
      this.occurrencesError = null
      
      try {
        const response = await api.get('/accounting/occurrences?page=1&page_size=10', {
          headers: this.getAuthHeaders()
        })
        this.occurrences = response.data
      } catch (err) {
        console.error('Erro ao carregar ocorrências:', err)
        this.occurrencesError = 'Erro ao carregar ocorrências'
      } finally {
        this.occurrencesLoading = false
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
        return format(new Date(dateString), 'dd/MM/yyyy HH:mm', { locale: ptBR })
      } catch {
        return dateString
      }
    },
    
    showDetails(occurrence) {
      console.log('Detalhes da ocorrência:', occurrence)
      // TODO: Abrir modal com detalhes
    }
  }
}
</script>

<style scoped>
.accounting-dashboard {
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

.severity.low {
  color: #f59e0b;
  font-weight: 500;
}

.severity.medium {
  color: #ef4444;
  font-weight: 500;
}

.severity.high {
  color: #991b1b;
  font-weight: 500;
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
}

.btn-sm:hover {
  background-color: #5568d3;
}
</style>
