<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-box">
        <div class="login-header">
          <h1>Pontix Cloud</h1>
          <p>Gestão de Presença e Ponto</p>
        </div>

        <!-- Error Alert -->
        <div v-if="error" class="alert alert-error">
          <span class="alert-icon">⚠️</span>
          <span>{{ error }}</span>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="login-form">
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
              placeholder="••••••••"
              required
              :disabled="loading"
            />
          </div>

          <button type="submit" class="btn-login" :disabled="loading">
            <span v-if="loading" class="spinner-btn"></span>
            <span>{{ loading ? 'Entrando...' : 'Entrar' }}</span>
          </button>
        </form>

        <!-- Footer -->
        <div class="login-footer">
          <p>Primeira vez aqui? <a href="#signup">Criar conta</a></p>
        </div>
      </div>

      <!-- Side Info -->
      <div class="login-side">
        <div class="side-content">
          <h2>Bem-vindo ao Pontix Cloud</h2>
          <ul class="features-list">
            <li>✓ Controle de presença com reconhecimento facial</li>
            <li>✓ Gestão completa de ocorrências</li>
            <li>✓ Relatórios em tempo real</li>
            <li>✓ Integração com RH e departamentos</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '@/services/api'

export default {
  name: 'Login',
  data() {
    return {
      email: '',
      password: '',
      loading: false,
      error: null
    }
  },
  mounted() {
    // Se já tiver token, redireciona
    if (localStorage.getItem('access_token')) {
      this.$router.push('/accounting')
    }
  },
  methods: {
    async handleLogin() {
      if (!this.email || !this.password) {
        this.error = 'Por favor, preencha todos os campos'
        return
      }

      this.loading = true
      this.error = null

      try {
        const response = await api.post('/auth/login', {
          email: this.email,
          password: this.password
        })

        // Armazenar token
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('user_role', response.data.role)

        // Redirecionar baseado no role
        const role = response.data.role
        if (role === 'owner') {
          this.$router.push('/owner')
        } else if (role === 'accounting') {
          this.$router.push('/accounting')
        } else {
          this.$router.push('/accounting')
        }
      } catch (err) {
        console.error('Erro ao fazer login:', err)
        this.error = err.response?.data?.detail || 'Erro ao fazer login. Verifique suas credenciais.'
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

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  height: 600px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.login-box {
  flex: 1;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 2rem;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.login-header p {
  color: #666;
  font-size: 0.95rem;
}

/* Error Alert */
.alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.alert-error {
  background-color: #fee;
  border-left: 4px solid #f87171;
  color: #7f1d1d;
  font-size: 0.9rem;
}

.alert-icon {
  font-size: 1.2rem;
}

/* Form */
.login-form {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.95rem;
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

/* Button */
.btn-login {
  width: 100%;
  padding: 0.85rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: inherit;
}

.btn-login:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.btn-login:disabled {
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
.login-footer {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.login-footer p {
  font-size: 0.9rem;
  color: #666;
}

.login-footer a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.login-footer a:hover {
  color: #5568d3;
}

/* Side Info */
.login-side {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3rem 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.side-content h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
}

.features-list {
  list-style: none;
  padding: 0;
}

.features-list li {
  margin-bottom: 1rem;
  font-size: 0.95rem;
  line-height: 1.5;
  opacity: 0.95;
}

/* Responsive */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    height: auto;
  }

  .login-box {
    padding: 2rem 1.5rem;
  }

  .login-side {
    display: none;
  }

  .login-header h1 {
    font-size: 1.5rem;
  }

  .login-header p {
    font-size: 0.85rem;
  }
}

@media (max-width: 480px) {
  .login-box {
    padding: 1.5rem 1rem;
  }

  .login-header {
    margin-bottom: 1.5rem;
  }

  .login-header h1 {
    font-size: 1.25rem;
  }

  .btn-login {
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
  }
}
</style>
