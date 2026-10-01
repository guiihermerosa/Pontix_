<template>
  <div id="app">
    <!-- Navigation (mostrar apenas se tiver token) -->
    <Navigation v-if="isLoggedIn" />
    
    <!-- Router view -->
    <router-view />
  </div>
</template>

<script>
import Navigation from './components/Navigation.vue'

export default {
  name: 'App',
  components: {
    Navigation
  },
  computed: {
    isLoggedIn() {
      return !!localStorage.getItem('access_token')
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f8f9fa;
  min-height: 100vh;
}

body {
  margin: 0;
  padding: 0;
}
</style>
