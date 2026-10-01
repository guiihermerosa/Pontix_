/**
 * Serviço de API para Pontix Cloud Frontend
 * Centraliza todas as chamadas HTTP para o backend
 */
import axios from 'axios'

// Obter URL base da API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// Criar instância do axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token de autenticação
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Interceptor para tratamento de erros
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expirado - redirecionar para login
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_id')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

/**
 * Endpoints de Autenticação
 */
export const authService = {
  register(email, password, fullName, companyName = null, cnpj = null) {
    return api.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
      company_name: companyName,
      cnpj,
    })
  },

  login(email, password) {
    return api.post('/api/auth/login', {
      email,
      password,
    })
  },

  refreshToken(refreshToken) {
    return api.post('/api/auth/refresh', {
      refresh_token: refreshToken,
    })
  },

  getCurrentUser() {
    return api.get('/api/auth/me')
  },

  logout() {
    return api.post('/api/auth/logout')
  },
}

/**
 * Endpoints do Painel do Contador
 */
export const accountingService = {
  getDashboard() {
    return api.get('/api/accounting/dashboard')
  },

  getEmployees(page = 1, pageSize = 10, search = null) {
    let url = `/api/accounting/employees?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    return api.get(url)
  },

  getTimeRecords(employeeId = null, startDate = null, endDate = null, page = 1, pageSize = 10) {
    let url = `/api/accounting/time-records?page=${page}&page_size=${pageSize}`
    if (employeeId) {
      url += `&employee_id=${employeeId}`
    }
    if (startDate) {
      url += `&start_date=${encodeURIComponent(startDate)}`
    }
    if (endDate) {
      url += `&end_date=${encodeURIComponent(endDate)}`
    }
    return api.get(url)
  },

  getOccurrences(status = null, employeeId = null, page = 1, pageSize = 10) {
    let url = `/api/accounting/occurrences?page=${page}&page_size=${pageSize}`
    if (status) {
      url += `&status=${status}`
    }
    if (employeeId) {
      url += `&employee_id=${employeeId}`
    }
    return api.get(url)
  },

  createOccurrence(employeeId, occurrenceType, occurrenceDate, severity = 'medium', description = null) {
    return api.post('/api/accounting/occurrences', {
      employee_id: employeeId,
      occurrence_type: occurrenceType,
      occurrence_date: occurrenceDate,
      severity,
      description,
    })
  },

  updateOccurrence(occurrenceId, status, resolutionNotes = null) {
    return api.put(`/api/accounting/occurrences/${occurrenceId}`, {
      status,
      resolution_notes: resolutionNotes,
    })
  },

  getJustifications(status = null, page = 1, pageSize = 10) {
    let url = `/api/accounting/justifications?page=${page}&page_size=${pageSize}`
    if (status) {
      url += `&status=${status}`
    }
    return api.get(url)
  },
}

/**
 * Endpoints do Painel do Proprietário
 */
export const ownerService = {
  getDashboard() {
    return api.get('/api/owner/dashboard')
  },

  getCompanies(page = 1, pageSize = 10, search = null) {
    let url = `/api/owner/companies?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    return api.get(url)
  },

  getCompany(companyId) {
    return api.get(`/api/owner/companies/${companyId}`)
  },

  updateCompany(companyId, data) {
    return api.put(`/api/owner/companies/${companyId}`, data)
  },

  getCompanyUsers(companyId, page = 1, pageSize = 10) {
    return api.get(`/api/owner/companies/${companyId}/users?page=${page}&page_size=${pageSize}`)
  },

  inviteUserToCompany(companyId, email, role = 'accountant') {
    return api.post(`/api/owner/companies/${companyId}/users/invite`, {
      email,
      role,
    })
  },

  getCompanyStatistics(companyId) {
    return api.get(`/api/owner/companies/${companyId}/statistics`)
  },
}

/**
 * Endpoints de Sincronização
 */
export const syncService = {
  syncEmployees(companyId, companyData, employees) {
    return api.post('/api/sync/employees', {
      company_id: companyId,
      company_data: companyData,
      employees,
    })
  },

  syncTimeRecords(companyId, timeRecords) {
    return api.post('/api/sync/time-records', {
      company_id: companyId,
      time_records: timeRecords,
    })
  },

  syncOccurrences(companyId, occurrences) {
    return api.post('/api/sync/occurrences', {
      company_id: companyId,
      occurrences,
    })
  },

  getSyncStatus(companyId) {
    return api.get(`/api/sync/status/${companyId}`)
  },
}

export { api }
export default api
