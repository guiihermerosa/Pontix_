<template>
  <div id="app">
    <nav class="navbar">
      <div class="navbar-brand">
        <h1>{{ title }}</h1>
      </div>
      <ul class="navbar-menu">
        <li><router-link to="/accounting">Contador</router-link></li>
        <li><router-link to="/owner">Proprietário</router-link></li>
        <li><a href="#" @click="logout">Sair</a></li>
      </ul>
    </nav>
    
    <div class="container">
      <router-view />
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      title: 'Pontix Cloud'
    }
  },
  methods: {
    logout() {
      // Limpar token e redirecionar para login
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_id')
      // Em um app real, redirecionar para /login
      console.log('Logout realizado')
      window.location.href = '/login'
    }
  }
}
</script>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

.navbar {
  background-color: #2c3e50;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.navbar-brand h1 {
  margin: 0;
  font-size: 1.5rem;
}

.navbar-menu {
  display: flex;
  list-style: none;
  gap: 2rem;
  margin: 0;
  padding: 0;
}

.navbar-menu a {
  color: white;
  text-decoration: none;
  transition: opacity 0.3s;
}

.navbar-menu a:hover {
  opacity: 0.7;
}

.container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
