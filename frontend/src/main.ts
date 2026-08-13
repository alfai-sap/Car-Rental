import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Apply the persisted theme before the app mounts to avoid a flash
// of the wrong theme on first paint.
useThemeStore(pinia)

app.mount('#app')

