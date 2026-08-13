<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import api from '@/services/api'
import { Upload, X, Pencil, ChevronDown, ChevronUp, ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff } from 'lucide-vue-next'

const auth = useAuthStore()
const error = ref('')
const success = ref('')
const resendingVerification = ref(false)

// ── Profile editing state ──
const editingProfile = ref(false)
const profileFirstName = ref('')
const profileLastName = ref('')
const profilePhone = ref('')
const profileSaving = ref(false)
const profileError = ref('')
const profileSuccess = ref('')

// ── Password change state ──
const showPasswordSection = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const showPassword = ref(false)
const passwordSaving = ref(false)
const passwordError = ref('')
const passwordSuccess = ref('')

const profileLocked = computed(() => !!(auth.user?.profile_locked || auth.user?.identity_locked))

function startEditProfile() {
  if (!auth.user) return
  profileFirstName.value = auth.user.first_name || ''
  profileLastName.value = auth.user.last_name || ''
  profilePhone.value = auth.user.phone || ''
  profileError.value = ''
  profileSuccess.value = ''
  editingProfile.value = true
}

function cancelEditProfile() {
  editingProfile.value = false
  profileError.value = ''
  profileSuccess.value = ''
}

async function saveProfile() {
  profileSaving.value = true
  profileError.value = ''
  profileSuccess.value = ''
  try {
    await auth.updateProfile({
      first_name: profileFirstName.value.trim(),
      last_name: profileLastName.value.trim(),
      phone: profilePhone.value.trim(),
    })
    profileSuccess.value = 'Profile updated.'
    editingProfile.value = false
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
    if (data) {
      profileError.value = Object.values(data).flat().join('. ')
    } else {
      profileError.value = 'Failed to update profile.'
    }
  } finally {
    profileSaving.value = false
  }
}

async function changePassword() {
  passwordSaving.value = true
  passwordError.value = ''
  passwordSuccess.value = ''
  try {
    await auth.changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
      new_password2: newPassword2.value,
    })
    passwordSuccess.value = 'Password changed. Please sign in again.'
    currentPassword.value = ''
    newPassword.value = ''
    newPassword2.value = ''
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
    if (data) {
      passwordError.value = Object.values(data).flat().join('. ')
    } else {
      passwordError.value = 'Failed to change password.'
    }
  } finally {
    passwordSaving.value = false
  }
}

// Lightbox state
const lightboxImage = ref('')
const lightboxZoom = ref(1)

function openLightbox(url: string) {
  lightboxImage.value = url
  lightboxZoom.value = 1
}

function closeLightbox() {
  lightboxImage.value = ''
  lightboxZoom.value = 1
}

function zoomIn() {
  lightboxZoom.value = Math.min(lightboxZoom.value + 0.5, 5)
}

function zoomOut() {
  lightboxZoom.value = Math.max(lightboxZoom.value - 0.5, 0.5)
}

function resetZoom() {
  lightboxZoom.value = 1
}

interface IdentityDoc {
  id: number
  document_type: string
  document_number: string
  front_image: string
  back_image: string | null
  submitted_at: string
  updated_at: string
}

const identityDocs = ref<IdentityDoc[]>([])

// Shared form state
const editingDocId = ref<number | null>(null)
const showAddForm = ref(false)
const documentType = ref('drivers_license')
const documentNumber = ref('')
const frontImage = ref<File | null>(null)
const frontPreview = ref('')
const backImage = ref<File | null>(null)
const backPreview = ref('')
const submittingDoc = ref(false)
const docError = ref('')
const docSuccess = ref('')
const expandedDocId = ref<number | null>(null)
const confirmDeleteId = ref<number | null>(null)

// ── Per-document-type placeholder examples ──
// No format validation is enforced — the placeholder is a visual guide only.
const DOCUMENT_FORMATS: Record<string, { placeholder: string }> = {
  drivers_license: { placeholder: 'XXX00-00-000000' },
  passport:         { placeholder: 'X0000000' },
  national_id:      { placeholder: '0000-0000000-0' },
  sss_id:           { placeholder: '00-0000000-0' },
  umid:             { placeholder: '0000-0000000-0' },
  prc_id:           { placeholder: '0000000' },
  postal_id:        { placeholder: '000000000000' },
}

// Maps legacy frontend values to backend values
const DOC_TYPE_MAP: Record<string, string> = {
  sss: 'sss_id',
  other: 'national_id',
}

function getDisplayLabel(type: string): string {
  const labels: Record<string, string> = {
    drivers_license: "Driver's License",
    passport: 'Passport',
    national_id: 'National ID (PhilSys)',
    sss_id: 'SSS ID',
    umid: 'UMID',
    prc_id: 'PRC ID',
    postal_id: 'Postal ID',
  }
  return labels[type] || type.replace(/_/g, ' ')
}

function onDocNumberInput(event: Event) {
  const input = event.target as HTMLInputElement
  documentNumber.value = input.value
}

// Update documentNumber when document type changes
function onDocTypeChange(event: Event) {
  const select = event.target as HTMLSelectElement
  documentType.value = select.value
}

// No special formatting — just trim whitespace before submitting
function getRawDocumentNumber(): string {
  return documentNumber.value.trim()
}

function onFrontImageChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) {
    frontImage.value = input.files[0]
    frontPreview.value = URL.createObjectURL(input.files[0])
  }
}

function onBackImageChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) {
    backImage.value = input.files[0]
    backPreview.value = URL.createObjectURL(input.files[0])
  }
}

function resetForm() {
  editingDocId.value = null
  documentType.value = 'drivers_license'
  documentNumber.value = ''
  frontImage.value = null
  backImage.value = null
  frontPreview.value = ''
  backPreview.value = ''
  docError.value = ''
  docSuccess.value = ''
}

function closeForm() {
  // Keep showAddForm false so we return to list view
  resetForm()
  showAddForm.value = false
  editingDocId.value = null
}

function startEdit(doc: IdentityDoc) {
  editingDocId.value = doc.id
  showAddForm.value = false
  documentType.value = doc.document_type
  documentNumber.value = doc.document_number
  frontImage.value = null
  backImage.value = null
  frontPreview.value = doc.front_image
  backPreview.value = doc.back_image || ''
  docError.value = ''
  docSuccess.value = ''
}

function toggleExpanded(docId: number) {
  expandedDocId.value = expandedDocId.value === docId ? null : docId
}

async function submitDocument() {
  docError.value = ''
  docSuccess.value = ''

  const isEdit = editingDocId.value !== null
  const hasNewFront = frontImage.value !== null

  if (!isEdit && (!documentNumber.value || !frontImage.value)) {
    docError.value = 'Document number and front image are required.'
    return
  }

  submittingDoc.value = true
  try {
    const formData = new FormData()
    formData.append('document_type', documentType.value)
    formData.append('document_number', getRawDocumentNumber())
    if (frontImage.value) formData.append('front_image', frontImage.value)
    if (backImage.value) formData.append('back_image', backImage.value)

    if (isEdit) {
      if (!hasNewFront) formData.delete('front_image')
      await api.put(`/identity-documents/${editingDocId.value}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      docSuccess.value = 'Document updated.'
    } else {
      await api.post('/identity-documents/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      docSuccess.value = 'Identity document submitted.'
    }

    closeForm()
    await fetchIdentityDocs()
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
    if (data) {
      docError.value = Object.values(data).flat().join('. ')
    } else {
      docError.value = 'Failed to save document.'
    }
  } finally {
    submittingDoc.value = false
  }
}

async function deleteDocument(docId: number) {
  try {
    await api.delete(`/identity-documents/${docId}/`)
    if (editingDocId.value === docId) closeForm()
    expandedDocId.value = null
    await fetchIdentityDocs()
  } catch {
    // ignore
  }
}

async function fetchIdentityDocs() {
  try {
    const response = await api.get('/identity-documents/')
    identityDocs.value = response.data
  } catch {
    // ignore
  }
}

async function resendVerification() {
  if (!auth.user) return
  resendingVerification.value = true
  try {
    await auth.resendVerification(auth.user.email)
    success.value = 'Verification email sent. Check your inbox.'
  } catch {
    error.value = 'Failed to resend verification email.'
  } finally {
    resendingVerification.value = false
  }
}

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUser()
  }
  fetchIdentityDocs()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-zinc-50">
    <Navbar />

    <div class="flex-1 max-w-2xl mx-auto px-4 pt-24 pb-16 w-full space-y-10">
      <h1 class="text-2xl font-semibold text-zinc-900 tracking-tight">Profile</h1>

      <!-- Profile Lock Indicator (top of page) -->
      <div v-if="profileLocked" class="rounded-md border border-amber-300 bg-amber-50 p-4 flex items-start gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <div>
          <p class="text-sm font-semibold text-amber-800">Profile is locked</p>
          <p class="text-sm text-amber-700 mt-0.5">
            You have an active booking, so your profile and identity information cannot be edited.
            Editing will be re-enabled once your booking is cancelled, rejected, or completed.
            You can still change your password below.
          </p>
        </div>
      </div>

      <!-- Unverified Banner -->
      <div v-if="auth.user && !auth.user.is_verified" class="rounded-md border border-amber-200 bg-amber-50 p-4">
        <p class="text-sm text-amber-800 font-medium">Your account is not verified.</p>
        <p class="text-sm text-amber-600 mt-1">Verify your email to enable transactions and rentals.</p>
        <button
          type="button"
          class="mt-3 text-sm font-medium text-amber-800 underline hover:text-amber-900"
          @click="resendVerification"
          :disabled="resendingVerification"
        >
          {{ resendingVerification ? 'Sending...' : 'Resend verification email' }}
        </button>
        <p v-if="success" class="text-sm text-green-600 mt-2">{{ success }}</p>
        <p v-if="error" class="text-sm text-red-600 mt-2">{{ error }}</p>
      </div>

      <!-- Account Details -->
      <section class="rounded-md border border-zinc-200 bg-white p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-zinc-900">Account Details</h2>
          <button
            v-if="!editingProfile && !profileLocked"
            type="button"
            class="text-xs font-medium text-zinc-500 hover:text-zinc-900 underline"
            @click="startEditProfile"
          >
            Edit
          </button>
          <span v-else-if="profileLocked" class="text-xs font-medium text-amber-600 flex items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            Locked
          </span>
        </div>

        <!-- View mode -->
        <dl v-if="!editingProfile" class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <dt class="text-zinc-500">Name</dt>
            <dd class="text-zinc-900">{{ auth.user?.first_name || '—' }} {{ auth.user?.last_name || '' }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500">Email</dt>
            <dd class="text-zinc-900">{{ auth.user?.email }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500">Phone</dt>
            <dd class="text-zinc-900">{{ auth.user?.phone || '—' }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500">Status</dt>
            <dd>
              <span v-if="auth.user?.is_verified" class="text-green-600">Verified</span>
              <span v-else class="text-amber-600">Unverified</span>
            </dd>
          </div>
        </dl>

        <!-- Edit mode -->
        <form v-else @submit.prevent="saveProfile" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>First Name</Label>
              <Input v-model="profileFirstName" type="text" required />
            </div>
            <div class="space-y-2">
              <Label>Last Name</Label>
              <Input v-model="profileLastName" type="text" required />
            </div>
          </div>
          <div class="space-y-2">
            <Label>Phone Number</Label>
            <Input
              v-model="profilePhone"
              type="tel"
              inputmode="numeric"
              maxlength="11"
              placeholder="09123456789"
            />
          </div>

          <p v-if="profileError" class="text-sm text-red-600">{{ profileError }}</p>
          <p v-if="profileSuccess" class="text-sm text-green-600">{{ profileSuccess }}</p>

          <div class="flex gap-2">
            <Button type="submit" size="sm" :disabled="profileSaving">
              {{ profileSaving ? 'Saving...' : 'Save Changes' }}
            </Button>
            <Button type="button" variant="ghost" size="sm" @click="cancelEditProfile">Cancel</Button>
          </div>
        </form>
      </section>

      <!-- Change Password (email/password accounts only) — collapsible -->
      <section v-if="auth.user?.auth_method !== 'google'" class="rounded-md border border-zinc-200 bg-white">
        <button
          type="button"
          class="w-full flex items-center justify-between p-6"
          @click="showPasswordSection = !showPasswordSection"
        >
          <h2 class="text-sm font-semibold text-zinc-900">Change Password</h2>
          <ChevronDown v-if="!showPasswordSection" class="h-4 w-4 text-zinc-400" />
          <ChevronUp v-else class="h-4 w-4 text-zinc-400" />
        </button>

        <div v-if="showPasswordSection" class="px-6 pb-6 border-t border-zinc-100 pt-5">
          <form @submit.prevent="changePassword" class="space-y-4">
            <div class="space-y-2">
              <Label>Current Password</Label>
              <Input v-model="currentPassword" :type="showPassword ? 'text' : 'password'" required />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>New Password</Label>
                <Input v-model="newPassword" :type="showPassword ? 'text' : 'password'" required />
              </div>
              <div class="space-y-2">
                <Label>Confirm New Password</Label>
                <Input v-model="newPassword2" :type="showPassword ? 'text' : 'password'" required />
              </div>
            </div>
            <label class="flex items-center gap-2 text-sm text-zinc-600">
              <input v-model="showPassword" type="checkbox" class="rounded" />
              Show passwords
            </label>

            <p v-if="passwordError" class="text-sm text-red-600">{{ passwordError }}</p>
            <p v-if="passwordSuccess" class="text-sm text-green-600">{{ passwordSuccess }}</p>

            <Button type="submit" size="sm" :disabled="passwordSaving">
              {{ passwordSaving ? 'Changing...' : 'Update Password' }}
            </Button>
          </form>
        </div>
      </section>

      <!-- Identity Documents -->
      <section class="rounded-md border border-zinc-200 bg-white p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-zinc-900">Identity Documents</h2>
          <button
            v-if="!showAddForm && editingDocId === null && !profileLocked"
            type="button"
            class="text-xs font-medium text-zinc-500 hover:text-zinc-900 underline"
            @click="showAddForm = true"
          >
            + Add Document
          </button>
        </div>

        <!-- Existing documents -->
        <div v-if="identityDocs.length" class="space-y-2 mb-4">
          <div
            v-for="doc in identityDocs"
            :key="doc.id"
            class="rounded border border-zinc-200"
          >
            <button
              type="button"
              class="w-full flex items-center justify-between p-4 text-sm text-left hover:bg-zinc-50 transition"
              @click="toggleExpanded(doc.id)"
            >
              <div>
                <p class="font-medium text-zinc-900">{{ getDisplayLabel(doc.document_type) }}</p>
                <p class="text-xs text-zinc-400 mt-0.5">
                  Updated {{ new Date(doc.updated_at).toLocaleDateString() }}
                </p>
              </div>
              <ChevronDown v-if="expandedDocId !== doc.id" class="h-4 w-4 text-zinc-400" />
              <ChevronUp v-else class="h-4 w-4 text-zinc-400" />
            </button>

            <div v-if="expandedDocId === doc.id" class="border-t border-zinc-100 p-4 space-y-3">
              <!-- Document Number (editable when editing) -->
              <div>
                <p class="text-xs text-zinc-500 mb-1">Document Number</p>
                <p v-if="editingDocId !== doc.id" class="text-sm text-zinc-900 font-mono">{{ doc.document_number }}</p>
                <Input
                  v-else
                  :model-value="documentNumber"
                  @input="onDocNumberInput"
                  type="text"
                  maxlength="50"
                  :placeholder="DOCUMENT_FORMATS[documentType]?.placeholder || 'Enter document number'"
                  required
                />
              </div>

              <!-- Document Type (shown when editing) -->
              <div v-if="editingDocId === doc.id" class="space-y-1">
                <Label>Document Type</Label>
                <select
                  v-model="documentType"
                  @change="onDocTypeChange"
                  class="h-10 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:border-transparent"
                >
                  <option value="drivers_license">Driver's License</option>
                  <option value="passport">Passport</option>
                  <option value="national_id">National ID (PhilSys)</option>
                  <option value="sss_id">SSS ID</option>
                  <option value="umid">UMID</option>
                  <option value="prc_id">PRC ID</option>
                  <option value="postal_id">Postal ID</option>
                </select>
              </div>

              <!-- Images (same layout for view and edit) -->
              <div class="flex gap-4">
                <div class="flex-1">
                  <p class="text-xs text-zinc-500 mb-1">Front</p>
                  <template v-if="editingDocId === doc.id">
                    <label class="flex flex-col items-center gap-1 p-3 border-2 border-dashed border-zinc-300 rounded-md cursor-pointer hover:border-zinc-400 transition">
                      <Upload v-if="!frontPreview" class="h-4 w-4 text-zinc-400" />
                      <img v-else :src="frontPreview" class="h-20 object-contain rounded" />
                      <span class="text-xs text-zinc-500">Change</span>
                      <input type="file" accept="image/*" class="hidden" @change="onFrontImageChange" />
                    </label>
                  </template>
                  <img v-else :src="doc.front_image" class="h-20 rounded border object-contain cursor-zoom-in hover:ring-2 hover:ring-zinc-400 transition" @click="openLightbox(doc.front_image)" />
                </div>
                <div class="flex-1">
                  <p class="text-xs text-zinc-500 mb-1">Back</p>
                  <template v-if="editingDocId === doc.id">
                    <label class="flex flex-col items-center gap-1 p-3 border-2 border-dashed border-zinc-300 rounded-md cursor-pointer hover:border-zinc-400 transition">
                      <Upload v-if="!backPreview" class="h-4 w-4 text-zinc-400" />
                      <img v-else :src="backPreview" class="h-20 object-contain rounded" />
                      <span class="text-xs text-zinc-500">Change</span>
                      <input type="file" accept="image/*" class="hidden" @change="onBackImageChange" />
                    </label>
                  </template>
                  <img v-else-if="doc.back_image" :src="doc.back_image" class="h-20 rounded border object-contain cursor-zoom-in hover:ring-2 hover:ring-zinc-400 transition" @click="openLightbox(doc.back_image!)" />
                  <p v-else class="text-xs text-zinc-400 italic">No back image</p>
                </div>
              </div>

              <!-- Error/Success -->
              <p v-if="editingDocId === doc.id && docError" class="text-sm text-red-600">{{ docError }}</p>
              <p v-if="editingDocId === doc.id && docSuccess" class="text-sm text-green-600">{{ docSuccess }}</p>

              <!-- Buttons -->
              <div class="flex gap-2 pt-2">
                <template v-if="editingDocId === doc.id && !profileLocked">
                  <Button type="button" @click="submitDocument" :disabled="submittingDoc" size="sm">
                    {{ submittingDoc ? 'Saving...' : 'Save Changes' }}
                  </Button>
                  <Button type="button" variant="ghost" size="sm" @click="closeForm()">Cancel</Button>
                </template>
                <template v-else-if="editingDocId === doc.id">
                  <Button type="button" variant="ghost" size="sm" @click="closeForm()">Close</Button>
                </template>
                <template v-else-if="!profileLocked">
                  <Button variant="outline" size="sm" @click="startEdit(doc)">
                    <Pencil class="h-3.5 w-3.5 mr-1.5" /> Edit
                  </Button>
                  <Button variant="outline" size="sm" class="!border-red-200 !text-red-600 hover:!bg-red-50" @click="confirmDeleteId = doc.id">
                    <X class="h-3.5 w-3.5 mr-1.5" /> Delete
                  </Button>
                </template>
              </div>
            </div>
          </div>
        </div>

        <p v-if="!identityDocs.length && !showAddForm" class="text-sm text-zinc-500">
          No identity documents submitted. Add your driver's license or valid ID.
        </p>

        <!-- Add new form -->
        <div v-if="showAddForm && editingDocId === null" class="space-y-3 pt-4 border-t border-zinc-100">
          <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider">New Document</h3>

          <div class="space-y-1">
            <Label>Document Type</Label>
            <select
              v-model="documentType"
              @change="onDocTypeChange"
              class="h-10 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:border-transparent"
            >
              <option value="drivers_license">Driver's License</option>
              <option value="passport">Passport</option>
              <option value="national_id">National ID (PhilSys)</option>
              <option value="sss_id">SSS ID</option>
              <option value="umid">UMID</option>
              <option value="prc_id">PRC ID</option>
              <option value="postal_id">Postal ID</option>
            </select>
          </div>

          <div class="space-y-1">
            <Label>Document Number</Label>
            <Input
              :model-value="documentNumber"
              @input="onDocNumberInput"
              type="text"
              :placeholder="DOCUMENT_FORMATS[documentType]?.placeholder || 'Enter document number'"
              maxlength="50"
              required
            />
          </div>

          <!-- Images for add form -->
          <div class="flex gap-4">
            <div class="flex-1">
              <p class="text-xs text-zinc-500 mb-1">Front Photo</p>
              <label class="flex flex-col items-center gap-1 p-3 border-2 border-dashed border-zinc-300 rounded-md cursor-pointer hover:border-zinc-400 transition">
                <Upload v-if="!frontPreview" class="h-4 w-4 text-zinc-400" />
                <img v-else :src="frontPreview" class="h-20 object-contain rounded" />
                <span class="text-xs text-zinc-500">{{ frontPreview ? 'Change' : 'Upload' }}</span>
                <input type="file" accept="image/*" class="hidden" @change="onFrontImageChange" />
              </label>
            </div>
            <div class="flex-1">
              <p class="text-xs text-zinc-500 mb-1">Back Photo</p>
              <label class="flex flex-col items-center gap-1 p-3 border-2 border-dashed border-zinc-300 rounded-md cursor-pointer hover:border-zinc-400 transition">
                <Upload v-if="!backPreview" class="h-4 w-4 text-zinc-400" />
                <img v-else :src="backPreview" class="h-20 object-contain rounded" />
                <span class="text-xs text-zinc-500">{{ backPreview ? 'Change' : 'Upload' }}</span>
                <input type="file" accept="image/*" class="hidden" @change="onBackImageChange" />
              </label>
            </div>
          </div>

          <p v-if="docError" class="text-sm text-red-600">{{ docError }}</p>
          <p v-if="docSuccess" class="text-sm text-green-600">{{ docSuccess }}</p>

          <div class="flex gap-2">
            <Button type="button" @click="submitDocument" :disabled="submittingDoc" size="sm">
              {{ submittingDoc ? 'Submitting...' : 'Submit' }}
            </Button>
            <Button type="button" variant="ghost" size="sm" @click="closeForm()">Cancel</Button>
          </div>
        </div>
      </section>

      <!-- Image Lightbox Modal -->
      <div
        v-if="lightboxImage"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
        @click.self="closeLightbox"
      >
        <!-- Close -->
        <button
          class="absolute top-4 right-4 text-white/70 hover:text-white z-10"
          @click="closeLightbox"
        >
          <X class="h-6 w-6" />
        </button>

        <!-- Zoom controls -->
        <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-zinc-900/80 rounded-lg px-4 py-2 z-10">
          <button
            class="text-white/70 hover:text-white p-1"
            @click="zoomOut"
            :disabled="lightboxZoom <= 0.5"
          >
            <ZoomOut class="h-5 w-5" />
          </button>
          <span class="text-white text-xs tabular-nums w-10 text-center">
            {{ Math.round(lightboxZoom * 100) }}%
          </span>
          <button
            class="text-white/70 hover:text-white p-1"
            @click="zoomIn"
            :disabled="lightboxZoom >= 5"
          >
            <ZoomIn class="h-5 w-5" />
          </button>
          <button
            class="text-white/70 hover:text-white p-1"
            @click="resetZoom"
            title="Reset zoom"
          >
            <RotateCcw class="h-4 w-4" />
          </button>
        </div>

        <!-- Image -->
        <div class="max-w-[90vw] max-h-[90vh] overflow-auto">
          <img
            :src="lightboxImage"
            :style="{ transform: `scale(${lightboxZoom})` }"
            class="max-w-none transition-transform duration-200 origin-center"
          />
        </div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div
        v-if="confirmDeleteId !== null"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div class="absolute inset-0 bg-black/30" @click="confirmDeleteId = null" />
        <div class="relative bg-white rounded-lg border border-zinc-200 shadow-lg max-w-sm w-full mx-4 p-6">
          <h3 class="text-sm font-semibold text-zinc-900 mb-2">Delete Document</h3>
          <p class="text-sm text-zinc-500 mb-6">
            Are you sure you want to delete this document? This action cannot be undone.
          </p>
          <div class="flex justify-end gap-2">
            <Button variant="ghost" size="sm" @click="confirmDeleteId = null">Cancel</Button>
            <button
              type="button"
              class="inline-flex items-center justify-center h-9 px-3 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 transition"
              @click="deleteDocument(confirmDeleteId!); confirmDeleteId = null"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
