import { createRouter, createWebHistory } from 'vue-router'
import Login from '../pages/Login.vue'
import AccountingDashboard from '../pages/AccountingDashboard.vue'
import OwnerDashboard from '../pages/OwnerDashboard.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/accounting'
  },
  {
    path: '/accounting',
    name: 'Accounting',
    component: AccountingDashboard,
    meta: { requiresAuth: true, roles: ['accounting', 'owner'] }
  },
  {
    path: '/owner',
    name: 'Owner',
    component: OwnerDashboard,
    meta: { requiresAuth: true, roles: ['owner'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Guard de proteção de rotas
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const userRole = localStorage.getItem('user_role')

  // Se a rota requer autenticação
  if (to.meta.requiresAuth !== false) {
    if (!token) {
      // Não tem token, redireciona para login
      next('/login')
      return
    }

    // Se tem roles específicas, verifica
    if (to.meta.roles && !to.meta.roles.includes(userRole)) {
      // Redireciona para o dashboard apropriado
      if (userRole === 'owner') {
        next('/owner')
      } else {
        next('/accounting')
      }
      return
    }
  } else if (to.path === '/login' && token) {
    // Se já tá logado e tenta acessar login, redireciona para dashboard
    next('/accounting')
    return
  }

  next()
})

export default router
