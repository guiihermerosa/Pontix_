<template>
  <div class="signup-page">
    <div class="signup-container">
      <div class="signup-box">
        <div class="signup-header">
          <h1>Criar Conta</h1>
          <p>Pontix Cloud</p>
        </div>

        <!-- Error Alert -->
        <div v-if="error" class="alert alert-error">
          <span class="alert-icon">⚠️</span>
          <span>{{ error }}</span>
        </div>

        <!-- Success Message -->
        <div v-if="success" class="alert alert-success">
          <span class="alert-icon">✓</span>
          <span>Conta criada com sucesso! Redirecionando...</span>
        </div>

        <!-- Signup Form -->
        <form v-if="!success" @submit.prevent="handleSignUp" class="signup-form">
          <div class="form-group">
            <label for="full_name">Nome Completo</label>
            <input
              id="full_name"
              v-model="fullName"
              type="text"
              placeholder="Seu nome completo"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="email">Email</label>
            <input
              id="email"
              v-model="email"
              type="email"
              placeholder="seu@email.com"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="password">Senha</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="Mínimo 8 caracteres"
              required
              minlength="8"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="confirm_password">Confirmar Senha</label>
            <input
              id="confirm_password"
              v-model="confirmPassword"
              type="password"
              placeholder="Confirme a senha"
              required
              :disabled="loading"
            />
          </div>

          <!-- Company Section -->
          <div class="divider">Dados da Empresa (Opcional)</div>

          <div class="form-group">
            <label for="company_name">Nome da Empresa</label>
            <input
              id="company_name"
              v-model="companyName"
              type="text"
              placeholder="Nome da sua empresa"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="cnpj">CNPJ</label>
            <input
              id="cnpj"
              v-model="cnpj"
              type="text"
              placeholder="00.000.000/0000-00"
              :disabled="loading"
            />
          </div>

          <button type="submit" class="btn-signup" :disabled="loading">
            <span v-if="loading" class="spinner-btn"></span>
            <span>{{ loading ? 'Criando conta...' : 'Criar Conta' }}</span>
          </button>
        </form>

        <!-- Footer -->
        <div class="signup-footer">
          <p>Já tem conta? <router-link to="/login">Fazer login</router-link></p>
        </div>
      </div>

      <!-- Side Info -->
      <div class="signup-side">
        <div class="side-content">
          <h2>Comece agora</h2>
          <ul class="benefits-list">
            <li>✓ Reconhecimento facial automático</li>
            <li>✓ Gestão simplificada de ponto</li>
            <li>✓ Relatórios em tempo real</li>
            <li>✓ Integração com RH</li>
            <li>✓ Suporte dedicado</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '@/services/api'

export default {
  name: 'SignUp',
  data() {
    return {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
      companyName: '',
      cnpj: '',
      loading: false,
      error: null,
      success: false
    }
  },
  mounted() {
    // Se já tiver token, redireciona
    if (localStorage.getItem('access_token')) {
      this.$router.push('/accounting')
    }
  },
  methods: {
    async handleSignUp() {
      // Validações
      if (!this.fullName.trim()) {
        this.error = 'Por favor, preencha seu nome completo'
        return
      }

      if (!this.email.trim()) {
        this.error = 'Por favor, preencha seu email'
        return
      }

      if (!this.password || this.password.length < 8) {
        this.error = 'A senha deve ter no mínimo 8 caracteres'
        return
      }

      if (this.password !== this.confirmPassword) {
        this.error = 'As senhas não conferem'
        return
      }

      this.loading = true
      this.error = null

      try {
        const response = await api.post('/auth/register', {
          full_name: this.fullName,
          email: this.email,
          password: this.password,
          company_name: this.companyName || undefined,
          cnpj: this.cnpj || undefined
        })

        // Armazenar token
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('user_role', 'owner')

        this.success = true

        // Redirecionar após 2 segundos
        setTimeout(() => {
          this.$router.push('/owner')
        }, 2000)
      } catch (err) {
        console.error('Erro ao criar conta:', err)
        this.error = err.response?.data?.detail || 'Erro ao criar conta. Tente novamente.'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.signup-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  padding: 1rem;
}

.signup-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.signup-box {
  flex: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-height: 90vh;
  overflow-y: auto;
}

.signup-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.signup-header h1 {
  font-size: 1.8rem;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.signup-header p {
  color: #666;
  font-size: 0.9rem;
}

/* Alert */
.alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

.alert-error {
  background-color: #fee;
  border-left: 4px solid #f87171;
  color: #7f1d1d;
}

.alert-success {
  background-color: #dcfce7;
  border-left: 4px solid #86efac;
  color: #166534;
}

.alert-icon {
  font-size: 1.2rem;
}

/* Form */
.signup-form {
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.4rem;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.65rem 0.9rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  background-color: #f9fafb;
  color: #999;
}

.divider {
  color: #999;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  margin: 1rem 0 0.75rem 0;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

/* Button */
.btn-signup {
  width: 100%;
  padding: 0.8rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: inherit;
  margin-top: 0.5rem;
}

.btn-signup:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.btn-signup:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner-btn {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Footer */
.signup-footer {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.signup-footer p {
  font-size: 0.9rem;
  color: #666;
}

.signup-footer a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.signup-footer a:hover {
  color: #5568d3;
}

/* Side Info */
.signup-side {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.side-content h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
}

.benefits-list {
  list-style: none;
  padding: 0;
}

.benefits-list li {
  margin-bottom: 1rem;
  font-size: 0.95rem;
  line-height: 1.5;
  opacity: 0.95;
}

/* Responsive */
@media (max-width: 768px) {
  .signup-container {
    flex-direction: column;
  }

  .signup-box {
    padding: 1.5rem;
    max-height: none;
  }

  .signup-side {
    display: none;
  }

  .signup-header h1 {
    font-size: 1.5rem;
  }

  .signup-header p {
    font-size: 0.85rem;
  }

  .form-group input {
    padding: 0.6rem 0.8rem;
    font-size: 0.85rem;
  }

  .btn-signup {
    padding: 0.7rem 1rem;
    font-size: 0.9rem;
  }
}

@media (max-width: 480px) {
  .signup-box {
    padding: 1rem;
  }

  .signup-header {
    margin-bottom: 1rem;
  }

  .signup-header h1 {
    font-size: 1.25rem;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .form-group label {
    font-size: 0.85rem;
    margin-bottom: 0.3rem;
  }

  .divider {
    margin: 0.75rem 0 0.5rem 0;
    padding-top: 0.75rem;
  }
}
</style>
