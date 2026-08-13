<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { Eye, EyeOff, Mail } from 'lucide-vue-next'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const errorCode = ref('')
const loading = ref(false)
const resendingVerification = ref(false)
const resendSent = ref(false)
const googleLoading = ref(false)
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

const isUnverified = computed(() => errorCode.value === 'email_unverified')

// ── Google Sign-In (OIDC) ──
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void
          renderButton: (el: HTMLElement, config: Record<string, unknown>) => void
        }
      }
    }
  }
}

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve) => {
    if (document.getElementById('google-gis-script')) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.id = 'google-gis-script'
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    document.head.appendChild(script)
  })
}

async function handleGoogleResponse(credential: string) {
  googleLoading.value = true
  error.value = ''
  errorCode.value = ''
  try {
    await auth.loginWithGoogle(credential)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err: unknown) {
    const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
    error.value = data?.detail || 'Google Sign-In failed. Please try again.'
  } finally {
    googleLoading.value = false
  }
}

async function initGoogleSignIn() {
  if (!googleClientId) return
  await loadGoogleScript()
  const win = window
  if (!win.google?.accounts?.id) return
  win.google.accounts.id.initialize({
    client_id: googleClientId,
    callback: (response: { credential?: string }) => {
      if (response?.credential) {
        handleGoogleResponse(response.credential)
      }
    },
  })
  const container = document.getElementById('googleSignInButton')
  if (container) {
    win.google.accounts.id.renderButton(container, {
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      shape: 'rectangular',
      width: 320,
    })
  }
}

onMounted(() => {
  initGoogleSignIn()
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  errorCode.value = ''
  resendSent.value = false
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err: unknown) {
    const response = (err as { response?: { data?: { detail?: string; code?: string; email?: string[]; password?: string[] } } })?.response
    const data = response?.data
    if (data?.code === 'email_unverified') {
      errorCode.value = 'email_unverified'
      error.value = 'Your email is not yet verified. Please check your inbox or request a new verification link below.'
    } else if (data?.detail) {
      error.value = data.detail
    } else if (data) {
      const messages = Object.values(data).flat().filter(Boolean)
      error.value = messages.join('. ') || 'Invalid email or password.'
    } else {
      error.value = 'Invalid email or password.'
    }
  } finally {
    loading.value = false
  }
}

async function resendVerification() {
  if (!email.value.trim()) return
  resendingVerification.value = true
  resendSent.value = false
  try {
    await auth.resendVerification(email.value)
    resendSent.value = true
  } catch {
    // silently handle — endpoint always returns 200 for anti-enumeration
  } finally {
    resendingVerification.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <div class="flex-1 flex items-center justify-center px-4 pt-16">
      <div class="w-full max-w-sm">
        <h1 class="text-2xl font-semibold text-zinc-900 text-center mb-8 tracking-tight">
          Sign In
        </h1>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <!-- Google Sign-In -->
          <div v-if="googleClientId" class="space-y-2">
            <div id="googleSignInButton" class="flex justify-center"></div>
            <div class="flex items-center gap-3 py-1">
              <span class="flex-1 h-px bg-zinc-200"></span>
              <span class="text-xs text-zinc-400">OR</span>
              <span class="flex-1 h-px bg-zinc-200"></span>
            </div>
          </div>

          <div class="space-y-2">
            <Label>Email</Label>
            <Input v-model="email" type="email" required />
          </div>

          <div class="space-y-2">
            <Label>Password</Label>
            <div class="relative">
              <Input v-model="password" :type="showPassword ? 'text' : 'password'" required class="pr-10" />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                @click="showPassword = !showPassword"
                tabindex="-1"
              >
                <EyeOff v-if="showPassword" class="h-4 w-4" />
                <Eye v-else class="h-4 w-4" />
              </button>
            </div>
          </div>

          <p v-if="error" class="text-sm" :class="isUnverified ? 'text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3' : 'text-red-600'">
            {{ error }}
          </p>

          <!-- Resend verification (only shown for unverified users) -->
          <div
            v-if="isUnverified"
            class="p-3 rounded-lg border border-blue-200 bg-blue-50 space-y-2"
          >
            <p class="text-sm text-blue-700 font-medium flex items-center gap-1.5">
              <Mail class="w-3.5 h-3.5" />
              Need a new verification link?
            </p>
            <p v-if="resendSent" class="text-xs text-green-700 bg-green-50 rounded p-2">
              If an unverified account with that email exists, a new verification link has been sent. Please check your inbox.
            </p>
            <Button
              variant="outline"
              size="sm"
              class="w-full"
              :disabled="resendingVerification || !email.trim()"
              @click="resendVerification"
            >
              {{ resendingVerification ? 'Sending...' : 'Resend Verification Email' }}
            </Button>
            <p class="text-xs text-blue-500">
              The verification link expires after 5 minutes. If it expired, request a new one above.
            </p>
          </div>

          <Button type="submit" class="w-full" :disabled="loading || googleLoading">
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </Button>

          <p class="text-sm text-center">
            <RouterLink to="/forgot-password" class="text-zinc-500 hover:text-zinc-900 hover:underline">
              Forgot your password?
            </RouterLink>
          </p>
        </form>

        <p class="text-sm text-center text-zinc-500 mt-6">
          Don't have an account?
          <RouterLink to="/register" class="text-zinc-900 font-medium hover:underline">
            Register
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>
