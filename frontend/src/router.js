import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './components/Dashboard.vue'
import BoardView from './components/BoardView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/board/:name', component: BoardView, props: true },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
