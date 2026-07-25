import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/blog',
    name: 'BlogList',
    component: () => import('../views/BlogList.vue')
  },
  {
    path: '/xhs',
    name: 'XhsCreator',
    component: () => import('../views/XhsCreator.vue')
  },
  {
    path: '/books',
    name: 'Books',
    component: () => import('../views/Books.vue')
  },
  {
    path: '/book/:id',
    name: 'BookReader',
    component: () => import('../views/BookReader.vue')
  },
  {
    path: '/reviewer',
    redirect: '/'
  },
  {
    path: '/blog/:id',
    name: 'BlogDetail',
    component: () => import('../views/BlogDetail.vue')
  },
  {
    path: '/generate/:taskId',
    name: 'Generate',
    component: () => import('../views/Generate.vue')
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/cron',
    redirect: (to) => ({
      path: '/dashboard',
      query: { ...to.query, tab: 'cron' }
    })
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
