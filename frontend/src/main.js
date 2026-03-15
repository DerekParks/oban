import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { router } from './router.js'
import { loadObsidianConfig } from './composables/useObsidian.js'

loadObsidianConfig()

createApp(App).use(router).mount('#app')
