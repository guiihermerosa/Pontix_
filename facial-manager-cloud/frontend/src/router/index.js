import { createRouter, createWebHistory } from 'vue-router'
import AccountingDashboard from '../pages/AccountingDashboard.vue'
import OwnerDashboard from '../pages/OwnerDashboard.vue'

const routes = [
  {
    path: '/',
    redirect: '/accounting'
  },
  {
    path: '/accounting',
    name: 'Accounting',
    component: AccountingDashboard
  },
  {
    path: '/owner',
    name: 'Owner',
    component: OwnerDashboard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
