import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/tokens.css'
import './assets/katex-overrides.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
