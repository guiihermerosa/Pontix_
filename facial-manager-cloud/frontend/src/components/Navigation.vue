<template>
  <nav class="navbar">
    <div class="nav-container">
      <div class="nav-brand">
        <h2>Pontix Cloud</h2>
      </div>

      <div class="nav-menu">
        <router-link 
          to="/accounting" 
          class="nav-link"
          :class="{ active: $route.path === '/accounting' }"
        >
          Contador
        </router-link>
        
        <router-link 
          v-if="userRole === 'owner'"
          to="/owner" 
          class="nav-link"
          :class="{ active: $route.path === '/owner' }"
        >
          Proprietário
        </router-link>
      </div>

      <div class="nav-user">
        <div class="user-info">
          <span class="user-role">{{ userRoleLabel }}</span>
        </div>
        <button class="btn-logout" @click="handleLogout">
          Sair
        </button>
      </div>
    </div>
  </nav>
</template>

<script>
export default {
  name: 'Navigation',
  data() {
    return {
      userRole: localStorage.getItem('user_role')
    }
  },
  computed: {
    userRoleLabel() {
      const role = this.userRole
      if (role === 'owner') return 'Proprietário'
      if (role === 'accounting') return 'Contador'
      return 'Usuário'
    }
  },
  methods: {
    handleLogout() {
      // Limpar localStorage
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_role')
      
      // Redirecionar para login
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.navbar {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid #e5e7eb;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 70px;
}

.nav-brand h2 {
  margin: 0;
  color: #667eea;
  font-size: 1.3rem;
  font-weight: 700;
}

.nav-menu {
  display: flex;
  gap: 2rem;
  flex: 1;
  margin: 0 2rem;
}

.nav-link {
  color: #666;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid transparent;
}

.nav-link:hover {
  color: #667eea;
}

.nav-link.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  text-align: right;
}

.user-role {
  display: block;
  font-size: 0.85rem;
  color: #999;
  font-weight: 500;
}

.btn-logout {
  padding: 0.5rem 1rem;
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.btn-logout:hover {
  background-color: #e5e7eb;
  color: #1f2937;
}

/* Responsive */
@media (max-width: 768px) {
  .nav-container {
    padding: 0 1rem;
    height: 60px;
  }

  .nav-brand h2 {
    font-size: 1.1rem;
  }

  .nav-menu {
    gap: 1rem;
    margin: 0 1rem;
    font-size: 0.9rem;
  }

  .nav-link {
    padding-bottom: 0.25rem;
  }

  .btn-logout {
    padding: 0.4rem 0.8rem;
    font-size: 0.8rem;
  }

  .user-role {
    font-size: 0.75rem;
  }
}

@media (max-width: 480px) {
  .nav-container {
    flex-wrap: wrap;
    gap: 1rem;
  }

  .nav-brand {
    width: 100%;
  }

  .nav-menu {
    order: 3;
    width: 100%;
    gap: 0.5rem;
    margin: 0;
    font-size: 0.85rem;
  }

  .nav-user {
    gap: 0.5rem;
  }

  .btn-logout {
    padding: 0.35rem 0.6rem;
    font-size: 0.75rem;
  }
}
</style>
