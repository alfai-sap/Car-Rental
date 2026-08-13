import { defineStore } from 'pinia'
import { ref } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'car-rental-theme'

function initialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  // Respect the user's OS preference on first visit.
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
  root.style.colorScheme = theme
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(initialTheme())
  applyTheme(theme.value)

  function setTheme(next: Theme) {
    theme.value = next
    applyTheme(next)
    localStorage.setItem(STORAGE_KEY, next)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  const isDark = () => theme.value === 'dark'

  return { theme, isDark, setTheme, toggleTheme }
})
