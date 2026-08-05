import { createApp, h } from 'vue'
import { createInertiaApp } from '@inertiajs/vue3'
import { createPinia } from 'pinia'

createInertiaApp({
  resolve: (name) => {
    const pages: Record<string, () => Promise<unknown>> = {
      Home: () => import('./pages/Home.vue'),
      About: () => import('./pages/About.vue'),
    }
    const loader = pages[name] || pages['Home']
    return loader()
  },
  setup({ el, App, props, plugin }) {
    const app = createApp({ render: () => h(App, props) })
    app.use(plugin)
    app.use(createPinia())
    app.mount(el)
  },
})