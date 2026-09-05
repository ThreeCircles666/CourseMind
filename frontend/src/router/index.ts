import { createRouter, createWebHistory } from 'vue-router'
import IndexView from '@/views/IndexView.vue'
import AboutView from '@/views/AboutView.vue'
import ChatView from '@/views/ChatView.vue'
import DocumentsView from '@/views/DocumentsView.vue'
import KnowledgeAskView from '@/views/KnowledgeAskView.vue'
import AuthView from '@/views/AuthView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'index', component: IndexView, meta: { requiresAuth: true } },
    { path: '/about', name: 'about', component: AboutView, meta: { requiresAuth: true } },
    { path: '/chat', name: 'chat', component: ChatView, meta: { requiresAuth: true } },
    { path: '/documents', name: 'documents', component: DocumentsView, meta: { requiresAuth: true } },
    { path: '/knowledge-ask', name: 'knowledge-ask', component: KnowledgeAskView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: AuthView, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: AuthView, meta: { guestOnly: true } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.isRestoring) await auth.restore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) return { name: 'index' }
  return true
})

export default router
