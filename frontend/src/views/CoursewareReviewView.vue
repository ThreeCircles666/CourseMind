<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getDocuments, type Document } from '@/api/documents'
import * as api from '@/api/review'
import type { CoursewareReview, Evidence, ReviewSection, QuickEntry, Erratum } from '@/api/review'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'
import ReviewMath from '@/components/ReviewMath.vue'
import ReviewDemo from '@/components/ReviewDemo.vue'
import ReviewSource from '@/components/ReviewSource.vue'
import { exportReview } from '@/utils/reviewExport'
import 'katex/dist/katex.min.css'

const { t, locale } = useI18n()
const route = useRoute(), router = useRouter()
const documents = ref<Document[]>([]), history = ref<api.ReviewListItem[]>([])
const selected = ref<string[]>([]), useVision = ref(false), review = ref<CoursewareReview | null>(null)
const busy = ref(false), exporting = ref(false), saving = ref(false), error = ref('')
const activeSection = ref(''), quick = ref(false), navOpen = ref(false), query = ref(''), filter = ref('all')
const resultIndex = ref(0), searchInput = ref<HTMLInputElement>()
const images = ref<Record<string, string>>({}), imageErrors = ref<Record<string, string>>({})
const pendingImages = new Map<string, Promise<void>>()
const original = ref<{ documentId: string; page: number; sectionId: string } | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined, observer: IntersectionObserver | undefined
let epoch = 0, disposed = false
const ready = computed(() => review.value?.status === 'ready')
const active = computed(() => review.value?.sections.find(s => s.id === activeSection.value) ?? review.value?.sections[0])
const kinds = ['definition', 'formula', 'rule', 'conclusion', 'steps'] as const
const entries = computed(() => review.value?.sections.flatMap(section => section.quick_reference.map((entry, index) => ({ ...entry, section, index }))) ?? [])
const filteredEntries = computed(() => entries.value.filter(e => (filter.value === 'all' || e.kind === filter.value) && matches(`${e.name} ${e.text} ${e.section.title} ${e.evidence.map(p => `p${p.page}`).join(' ')}`)))
const results = computed(() => {
  if (!query.value.trim() || !ready.value) return []
  const found: { id: string; title: string; category: string; quick: boolean }[] = []
  for (const section of review.value!.sections) {
    if (matches([section.title, ...section.blocks.map(b => b.text), ...section.takeaways.map(b => b.text), ...section.pages.map(p => `p${p}`)].join(' ')))
      found.push({ id: section.id, title: section.title, category: t('review.summary'), quick: false })
    section.quick_reference.forEach((entry, index) => {
      if (matches(`${entry.name} ${entry.text} ${entry.evidence.map(e => `p${e.page}`).join(' ')}`))
        found.push({ id: `quick-${section.id}-${index}`, title: entry.name, category: t(`review.${entry.kind}`), quick: true })
    })
  }
  return found.slice(0, 40)
})
const progress = computed(() => review.value?.sections.length ? Math.round(review.value.reviewed_sections.length / review.value.sections.length * 100) : 0)
const currentDocument = computed(() => review.value?.documents.find(d => d.id === original.value?.documentId))
const currentPage = computed(() => currentDocument.value?.pages.find(p => p.number === original.value?.page))

function matches(text: string) { return text.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase()) }
function docName(id: string) { return review.value?.documents.find(d => d.id === id)?.name ?? documents.value.find(d => d.id === id)?.original_name ?? id }
function key(documentId: string, page: number) { return `${documentId}:${page}` }
function pageData(documentId: string, page: number) { return review.value?.documents.find(d => d.id === documentId)?.pages.find(p => p.number === page) }
function clearImages() { Object.values(images.value).forEach(URL.revokeObjectURL); images.value = {}; imageErrors.value = {}; pendingImages.clear() }
async function image(documentId: string, page: number) {
  const current = review.value
  if (!current || !pageData(documentId, page)?.has_image) return
  const imageKey = key(documentId, page)
  if (images.value[imageKey]) return
  if (pendingImages.has(imageKey)) return pendingImages.get(imageKey)
  const requestEpoch = epoch
  const task = api.getPageImage(current.id, documentId, page).then(blob => {
    if (epoch === requestEpoch && !disposed) images.value[imageKey] = URL.createObjectURL(blob)
  }).catch(e => { if (epoch === requestEpoch) imageErrors.value[imageKey] = String(e.message) }).finally(() => { if (epoch === requestEpoch) pendingImages.delete(imageKey) })
  pendingImages.set(imageKey, task)
  return task
}
function source(section: ReviewSection, evidence: Evidence) { return { evidence, name: docName(section.document_id), image: images.value[key(section.document_id, evidence.page)] } }
function openOriginal(section: ReviewSection, evidence: Evidence) {
  original.value = { documentId: section.document_id, page: evidence.page, sectionId: section.id }
  void image(section.document_id, evidence.page)
}
function changePage(delta: number) {
  if (!original.value || !currentDocument.value) return
  const page = original.value.page + delta
  if (currentDocument.value.pages.some(p => p.number === page)) {
    original.value.page = page
    original.value.sectionId = review.value!.sections.find(s => s.document_id === original.value!.documentId && s.pages.includes(page))?.id ?? original.value.sectionId
    void image(original.value.documentId, page)
  }
}
async function go(id: string, quickView = false) {
  quick.value = quickView; navOpen.value = false
  if (quickView) { query.value = ''; filter.value = 'all' }
  await nextTick()
  const element = document.getElementById(id)
  element?.scrollIntoView({ behavior: 'instant' as ScrollBehavior, block: 'start' })
  element?.focus({ preventScroll: true }); element?.classList.add('review-highlight')
  setTimeout(() => element?.classList.remove('review-highlight'), 1600)
  if (!quickView) activeSection.value = element?.closest('.review-section')?.id ?? id
  query.value = ''
  bindObserver()
}
function locate(section: ReviewSection, entry: QuickEntry) {
  const index = section.blocks.findIndex(block => block.text.includes(entry.name) || block.evidence.some(e => entry.evidence.some(p => p.page === e.page)))
  void go(index < 0 ? section.id : `block-${section.id}-${index}`)
  activeSection.value = section.id
}
function related(section: ReviewSection, index: number) {
  return section.quick_reference.map((entry, entryIndex) => ({ entry, entryIndex })).filter(({ entry }) => {
    const target = section.blocks.findIndex(block => block.text.includes(entry.name))
    return (target >= 0 ? target : section.blocks.findIndex(block => block.evidence.some(e => entry.evidence.some(p => p.page === e.page)))) === index
  })
}
function bindObserver() {
  observer?.disconnect()
  if (!ready.value || quick.value) return
  observer = new IntersectionObserver(items => {
    const visible = items.filter(i => i.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
    if (visible[0]) activeSection.value = visible[0].target.id
  }, { rootMargin: '-100px 0px -55% 0px', threshold: 0 })
  document.querySelectorAll('.review-section').forEach(element => observer!.observe(element))
}
async function refreshHistory() { history.value = await api.listReviews() }
async function load(id: string, reset = true) {
  clearTimeout(timer)
  if (reset) { epoch++; clearImages(); review.value = null; error.value = ''; quick.value = false; original.value = null }
  const requestEpoch = epoch
  try {
    const data = await api.getReview(id)
    if (disposed || requestEpoch !== epoch) return
    review.value = data
    if (!data.sections.some(s => s.id === activeSection.value)) activeSection.value = data.sections[0]?.id ?? ''
    if (data.status === 'queued' || data.status === 'processing') timer = setTimeout(() => void load(id, false), 2500)
    if (data.status === 'ready') { await nextTick(); bindObserver() }
    if (reset) void router.replace({ query: { review: id } })
  } catch (e) { if (requestEpoch === epoch) error.value = (e as Error).message }
}
async function generate() {
  if (!selected.value.length) return
  busy.value = true; error.value = ''
  try { const created = await api.createReview(selected.value, locale.value, useVision.value); await load(created.id); await refreshHistory() }
  catch (e) { error.value = (e as Error).message }
  finally { busy.value = false }
}
async function mark(sectionId: string) {
  if (!review.value || saving.value) return
  const reviewed = review.value.reviewed_sections.includes(sectionId) ? review.value.reviewed_sections.filter(id => id !== sectionId) : [...review.value.reviewed_sections, sectionId]
  await save({ reviewed_sections: reviewed })
}
async function save(patch: Parameters<typeof api.updateReview>[1]) {
  if (!review.value || saving.value) return
  const id = review.value.id
  saving.value = true
  try { const state = await api.updateReview(id, patch); if (review.value?.id === id) review.value = state }
  catch (e) { ElMessage.error((e as Error).message) }
  finally { saving.value = false }
}
async function decide(candidate: Erratum, decision: Erratum['status']) { await save({ erratum_id: candidate.id, decision }) }
async function remove(id: string) {
  try { await api.deleteReview(id); if (review.value?.id === id) { epoch++; clearTimeout(timer); clearImages(); review.value = null; void router.replace({ query: {} }) }; await refreshHistory() }
  catch (e) { error.value = (e as Error).message }
}
async function download() {
  if (!review.value || exporting.value) return
  exporting.value = true
  try { await exportReview(review.value, t) }
  catch (e) { ElMessage.error((e as Error).message) }
  finally { exporting.value = false }
}
function searchKey(event: KeyboardEvent) {
  if (event.key === 'Escape') { query.value = ''; return }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault(); resultIndex.value = Math.max(0, Math.min(results.value.length - 1, resultIndex.value + (event.key === 'ArrowDown' ? 1 : -1)))
  }
  if (event.key === 'Enter' && results.value[resultIndex.value]) {
    const result = results.value[resultIndex.value]; void go(result.id, result.quick)
  }
}
function shortcut(event: KeyboardEvent) {
  if (event.key === '/' && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) { event.preventDefault(); searchInput.value?.focus() }
}
watch(query, () => { resultIndex.value = 0 })
watch(() => route.query.review, id => { if (typeof id === 'string' && review.value?.id !== id) void load(id) })
watch(active, section => { if (section) void image(section.document_id, section.pages[0]) })
watch(quick, () => void nextTick(bindObserver))
onMounted(async () => {
  document.addEventListener('keydown', shortcut)
  try {
    const [docs] = await Promise.all([getDocuments(), refreshHistory()]); documents.value = docs
    if (typeof route.query.document === 'string') selected.value = [route.query.document]
    if (typeof route.query.review === 'string') await load(route.query.review)
  } catch (e) { error.value = (e as Error).message }
})
onBeforeUnmount(() => { disposed = true; epoch++; clearTimeout(timer); observer?.disconnect(); clearImages(); document.removeEventListener('keydown', shortcut) })
</script>

<template>
  <div class="review-workspace">
    <header class="review-toolbar">
      <router-link to="/">
        CourseMind
      </router-link><h1>{{ t('review.title') }}</h1>
      <div
        v-if="ready"
        class="review-search"
      >
        <input
          ref="searchInput"
          v-model="query"
          :placeholder="t('review.search')"
          :aria-label="t('review.search')"
          role="combobox"
          :aria-expanded="results.length > 0"
          aria-controls="review-search-results"
          :aria-activedescendant="results.length ? `search-result-${resultIndex}` : undefined"
          @keydown="searchKey"
        >
        <div
          v-if="query && !quick"
          id="review-search-results"
          role="listbox"
          class="search-results"
        >
          <button
            v-for="(result, index) in results"
            :id="`search-result-${index}`"
            :key="result.id"
            role="option"
            :aria-selected="index === resultIndex"
            :class="{ selected: index === resultIndex }"
            @click="go(result.id, result.quick)"
          >
            <small>{{ result.category }}</small> {{ result.title }}
          </button><p v-if="!results.length">
            {{ t('review.noResults') }}
          </p>
        </div>
      </div>
      <button
        v-if="ready"
        :aria-pressed="quick"
        @click="quick = !quick"
      >
        {{ t(quick ? 'review.summary' : 'review.quickReference') }}
      </button>
      <button
        v-if="ready"
        :disabled="exporting"
        @click="download"
      >
        {{ t(exporting ? 'review.exporting' : 'review.export') }}
      </button>
      <button
        v-if="ready"
        class="mobile-nav"
        :aria-expanded="navOpen"
        @click="navOpen = !navOpen"
      >
        {{ t('review.contents') }}
      </button><LocaleSwitcher />
    </header>
    <main>
      <section class="review-setup">
        <div><h2>{{ t('review.introTitle') }}</h2><p>{{ t('review.intro') }}</p></div>
        <label>{{ t('review.selectDocuments') }}<el-select
          v-model="selected"
          multiple
          :multiple-limit="8"
          :placeholder="t('review.selectDocuments')"
        ><el-option
          v-for="doc in documents"
          :key="doc.id"
          :label="doc.original_name"
          :value="doc.id"
        /></el-select></label>
        <label class="vision-option"><input
          v-model="useVision"
          type="checkbox"
        >{{ t('review.vision') }}<small>{{ t('review.visionHelp') }}</small></label>
        <button
          class="primary"
          :disabled="busy || !selected.length"
          @click="generate"
        >
          {{ t(busy ? 'review.starting' : 'review.generate') }}
        </button>
        <label v-if="history.length">{{ t('review.history') }}<select
          :value="review?.id ?? ''"
          @change="load(($event.target as HTMLSelectElement).value)"
        ><option
          value=""
          disabled
        >{{ t('review.history') }}</option><option
          v-for="item in history"
          :key="item.id"
          :value="item.id"
        >{{ new Date(item.created_at).toLocaleString() }} · {{ item.document_ids.map(docName).join(', ') }} · {{ t(`review.${item.status}`) }}</option></select></label>
      </section>
      <p
        v-if="error"
        role="alert"
        class="review-error"
      >
        {{ error }}
      </p>
      <section
        v-if="review && !ready"
        class="review-status"
        aria-live="polite"
      >
        <h2>{{ t(`review.${review.status}`) }}</h2><p>{{ t('review.completedPages', { count: review.completed_pages }) }}</p><p
          v-if="review.error"
          role="alert"
        >
          {{ t('review.failureHelp') }}
        </p><p v-else>
          {{ t('review.jobHelp') }}
        </p><button @click="load(review!.id)">
          {{ t('review.refresh') }}
        </button><button @click="remove(review!.id)">
          {{ t('review.remove') }}
        </button>
      </section>
      <div
        v-if="ready && review"
        class="review-layout"
        :class="{ 'quick-layout': quick }"
      >
        <nav
          class="review-toc"
          :class="{ 'is-open': navOpen }"
          :aria-label="t('review.contents')"
        >
          <strong>{{ t('review.contents') }}</strong><p>{{ t('review.progress') }} {{ progress }}%</p><progress
            :value="progress"
            max="100"
          /><button
            v-for="section in review.sections"
            :key="section.id"
            :class="{ current: activeSection === section.id }"
            :aria-current="activeSection === section.id ? 'location' : undefined"
            @click="go(section.id)"
          >
            <span>{{ review.reviewed_sections.includes(section.id) ? '✓ ' : '' }}{{ section.title }}</span><small>{{ docName(section.document_id) }} · {{ section.pages.map(p => `p${p}`).join(', ') }}</small>
          </button>
        </nav>
        <div class="review-reading">
          <section class="review-overview">
            <h2>{{ t(quick ? 'review.quickReference' : 'review.summary') }}</h2><p
              v-for="doc in review.documents"
              :key="doc.id"
            >
              {{ doc.name }} · {{ t('review.pageCount', { count: doc.pages.length }) }}
            </p><p class="review-boundary">
              {{ review.use_vision ? t('review.visionBoundary') : t('review.textBoundary') }}
            </p><div class="review-legend">
              <span
                v-for="kind in ['quote', 'explanation', 'inference', 'missing', 'takeaways', 'candidate']"
                :key="kind"
                :class="kind"
              >{{ t(`review.${kind}`) }}</span>
            </div><p
              v-for="(duplicate, index) in review.duplicates"
              :key="index"
            >
              {{ t('review.duplicate') }}: {{ docName(duplicate.document_id) }} p{{ duplicate.page }} ↔ {{ docName(duplicate.other_document_id) }} p{{ duplicate.other_page }}
            </p>
          </section>
          <template v-if="!quick">
            <article
              v-for="section in review.sections"
              :id="section.id"
              :key="section.id"
              class="review-section"
              tabindex="-1"
            >
              <header><small>{{ docName(section.document_id) }} · {{ section.pages.map(p => `p${p}`).join(', ') }}</small><h2>{{ section.title }}</h2></header>
              <div
                v-for="(block, index) in section.blocks"
                :id="`block-${section.id}-${index}`"
                :key="index"
                class="review-block"
                :class="block.kind"
                tabindex="-1"
              >
                <small class="block-kind">{{ t(`review.${block.kind}`) }}</small>
                <pre v-if="block.kind === 'code'"><code>{{ block.text }}</code></pre>
                <template v-else-if="block.kind === 'table'">
                  <ReviewMath :text="block.text" /><div class="table-scroll">
                    <table>
                      <tbody>
                        <tr
                          v-for="(row, r) in block.rows"
                          :key="r"
                        >
                          <component
                            :is="r === 0 ? 'th' : 'td'"
                            v-for="(cell, c) in row"
                            :key="c"
                          >
                            <ReviewMath :text="cell" />
                          </component>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </template>
                <ReviewMath
                  v-else
                  :text="block.text"
                  :formula="block.kind === 'formula'"
                />
                <ReviewSource
                  v-for="(evidence, e) in block.evidence"
                  :key="e"
                  v-bind="source(section, evidence)"
                  @preview="image(section.document_id, evidence.page)"
                  @open="openOriginal(section, evidence)"
                />
                <button
                  v-for="link in related(section, index)"
                  :key="link.entryIndex"
                  class="term-link"
                  @click="go(`quick-${section.id}-${link.entryIndex}`, true)"
                >
                  {{ link.entry.name }} · {{ t('review.quickReference') }}
                </button>
              </div>
              <template
                v-for="(demo, index) in section.demos"
                :key="`demo-${index}`"
              >
                <ReviewDemo :demo="demo" /><ReviewSource
                  v-for="(evidence, e) in demo.evidence"
                  :key="e"
                  v-bind="source(section, evidence)"
                  @preview="image(section.document_id, evidence.page)"
                  @open="openOriginal(section, evidence)"
                />
              </template>
              <section
                v-for="candidate in section.errata"
                :key="candidate.id"
                class="review-erratum"
              >
                <strong>{{ t('review.erratum') }} · {{ t(`review.${candidate.status}`) }}</strong><p>{{ t('review.original') }}: {{ candidate.original }}</p><p>{{ t('review.correction') }}: {{ candidate.correction }}</p><ReviewMath :text="candidate.reason" /><p>{{ t('review.impact') }}: {{ candidate.impact }}</p><p>{{ t('review.errataHelp') }}</p><ReviewSource
                  v-for="(evidence, e) in candidate.evidence"
                  :key="e"
                  v-bind="source(section, evidence)"
                  @preview="image(section.document_id, evidence.page)"
                  @open="openOriginal(section, evidence)"
                /><div>
                  <button
                    :disabled="saving || candidate.status === 'confirmed'"
                    @click="decide(candidate, 'confirmed')"
                  >
                    {{ t('review.confirm') }}
                  </button><button
                    :disabled="saving || candidate.status === 'dismissed'"
                    @click="decide(candidate, 'dismissed')"
                  >
                    {{ t('review.dismiss') }}
                  </button><button
                    v-if="candidate.status !== 'candidate'"
                    :disabled="saving"
                    @click="decide(candidate, 'candidate')"
                  >
                    {{ t('review.reset') }}
                  </button>
                </div>
              </section>
              <section
                v-if="section.takeaways.length"
                class="review-takeaways"
              >
                <h3>{{ t('review.takeaways') }}</h3><div
                  v-for="(entry, index) in section.takeaways"
                  :key="index"
                >
                  <button
                    class="takeaway-link"
                    @click="locate(section, entry)"
                  >
                    <ReviewMath :text="entry.text" />
                  </button><ReviewSource
                    v-for="(evidence, e) in entry.evidence"
                    :key="e"
                    v-bind="source(section, evidence)"
                    @preview="image(section.document_id, evidence.page)"
                    @open="openOriginal(section, evidence)"
                  />
                </div>
              </section>
              <button
                :disabled="saving"
                :aria-pressed="review.reviewed_sections.includes(section.id)"
                @click="mark(section.id)"
              >
                {{ t(review.reviewed_sections.includes(section.id) ? 'review.reviewed' : 'review.markReviewed') }}
              </button>
            </article>
          </template>
          <section
            v-else
            class="review-quick"
          >
            <div class="quick-filters">
              <button
                :aria-pressed="filter === 'all'"
                @click="filter = 'all'"
              >
                {{ t('review.all') }} ({{ entries.length }})
              </button><button
                v-for="kind in kinds.filter(k => entries.some(e => e.kind === k))"
                :key="kind"
                :aria-pressed="filter === kind"
                @click="filter = kind"
              >
                {{ t(`review.${kind}`) }} ({{ entries.filter(e => e.kind === kind).length }})
              </button>
            </div><p v-if="!filteredEntries.length">
              {{ t('review.noResults') }}
            </p><template
              v-for="doc in review.documents"
              :key="doc.id"
            >
              <h3 v-if="filteredEntries.some(e => e.section.document_id === doc.id)">
                {{ doc.name }}
              </h3><details
                v-for="section in review.sections.filter(s => s.document_id === doc.id && filteredEntries.some(e => e.section.id === s.id))"
                :key="section.id"
                open
              >
                <summary>{{ section.title }}</summary><article
                  v-for="entry in filteredEntries.filter(e => e.section.id === section.id)"
                  :id="`quick-${section.id}-${entry.index}`"
                  :key="entry.index"
                  tabindex="-1"
                >
                  <small>{{ t(`review.${entry.kind}`) }}</small><h4>{{ entry.name }}</h4><ReviewMath :text="entry.text" /><ReviewSource
                    v-for="(evidence, e) in entry.evidence"
                    :key="e"
                    v-bind="source(section, evidence)"
                    @preview="image(section.document_id, evidence.page)"
                    @open="openOriginal(section, evidence)"
                  /><button
                    class="term-link"
                    @click="locate(section, entry)"
                  >
                    {{ t('review.backToText') }}
                  </button>
                </article>
              </details>
            </template>
          </section>
        </div>
        <aside
          v-if="!quick && active"
          class="review-originals"
        >
          <h3>{{ t('review.originalPages') }}</h3><p>{{ docName(active.document_id) }}</p><button
            v-for="page in active.pages"
            :key="page"
            class="original-thumbnail"
            @mouseenter="image(active.document_id, page)"
            @focus="image(active.document_id, page)"
            @click="openOriginal(active, { page, quote: '' })"
          >
            <img
              v-if="images[key(active.document_id, page)]"
              :src="images[key(active.document_id, page)]"
              :alt="`p${page}`"
            ><span>p{{ page }} · {{ t('review.openOriginal') }}</span>
          </button>
        </aside>
      </div>
    </main>
    <el-dialog
      :model-value="Boolean(original)"
      :title="`${currentDocument?.name ?? ''} · p${original?.page ?? ''}`"
      width="min(1100px, 96vw)"
      @update:model-value="(value: boolean) => { if (!value) original = null }"
    >
      <template v-if="original">
        <img
          v-if="images[key(original.documentId, original.page)]"
          class="original-full"
          :src="images[key(original.documentId, original.page)]"
          :alt="`${currentDocument?.name}, p${original.page}`"
        ><p v-else-if="currentPage?.has_image">
          {{ imageErrors[key(original.documentId, original.page)] || t('review.loadingImage') }}<button
            v-if="imageErrors[key(original.documentId, original.page)]"
            @click="image(original.documentId, original.page)"
          >
            {{ t('review.refresh') }}
          </button>
        </p><pre
          v-else
          class="source-text"
        >{{ currentPage?.text }}</pre><details v-if="currentPage?.visual_description">
          <summary>{{ t('review.visualDescription') }}</summary><p>{{ currentPage.visual_description }}</p>
        </details><div class="original-controls">
          <button
            :disabled="original.page <= 1"
            @click="changePage(-1)"
          >
            {{ t('review.previous') }}
          </button><button
            :disabled="original.page >= (currentDocument?.pages.length ?? 0)"
            @click="changePage(1)"
          >
            {{ t('review.next') }}
          </button><button @click="go(original.sectionId); original = null">
            {{ t('review.backToText') }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.review-workspace { color: var(--cm-text-primary); background: var(--cm-bg-primary); min-height: 100vh; font-size: 15px; }
.review-toolbar { display: flex; align-items: center; gap: .8rem; padding: .8rem 1.5rem; position: sticky; top: 0; background: var(--cm-bg-primary); border-bottom: 1px solid var(--cm-border-light); z-index: 20; flex-wrap: wrap; }
.review-toolbar h1 { font-size: 1.05rem; margin: 0; white-space: nowrap; } .review-toolbar a { font-weight: 700; color: var(--cm-text-primary); text-decoration: none; }
button, select, input { font: inherit; } button { cursor: pointer; border: 1px solid var(--cm-border-light); border-radius: 6px; padding: .45rem .7rem; background: var(--cm-bg-primary); color: inherit; } button:disabled { opacity: .5; cursor: default; } button:hover:not(:disabled), button[aria-pressed=true] { background: var(--cm-bg-secondary); } button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--cm-primary); outline-offset: 2px; }
.review-search { flex: 1; min-width: 180px; position: relative; } input:not([type=checkbox]), select { border: 1px solid var(--cm-border-light); border-radius: 6px; padding: .5rem; width: 100%; background: var(--cm-bg-primary); color: inherit; } .search-results { position: absolute; top: 100%; width: 100%; max-height: 400px; overflow: auto; border: 1px solid var(--cm-border-light); background: var(--cm-bg-primary); z-index: 30; } .search-results button { display: block; width: 100%; text-align: left; border: 0; } .search-results button.selected { background: var(--cm-bg-secondary); } small { color: var(--cm-text-secondary); }
main { max-width: 1700px; margin: auto; padding: 1.5rem; } .review-setup { display: flex; flex-wrap: wrap; align-items: end; gap: 1rem; padding: 1.5rem; border: 1px solid var(--cm-border-light); border-radius: 12px; margin-bottom: 1.5rem; } .review-setup>div { flex: 1 1 100%; } .review-setup h2 { margin: 0; font-size: 1.25rem; } .review-setup p { color: var(--cm-text-secondary); margin-bottom: 0; } .review-setup label { display: grid; gap: .4rem; flex: 1 1 240px; } .vision-option { max-width: 340px; } .vision-option input { width: fit-content; } .primary { background: var(--cm-primary); color: white; min-height: 40px; } .primary:hover:not(:disabled) { color: var(--cm-text-primary); } .review-error { padding: 1rem; border: 1px solid var(--cm-border-light); color: var(--cm-danger, #b91c1c); } .review-status { padding: 2rem; }
.review-layout { display: grid; grid-template-columns: 220px minmax(0, 1fr) 240px; gap: 2rem; align-items: start; } .quick-layout { grid-template-columns: 220px minmax(0, 1fr); } .review-toc, .review-originals { position: sticky; top: 90px; max-height: calc(100vh - 110px); overflow: auto; } .review-toc button { display: block; width: 100%; text-align: left; padding: .7rem; border: 0; border-radius: 0; border-left: 2px solid transparent; } .review-toc button.current { border-left-color: var(--cm-primary); background: var(--cm-bg-secondary); } .review-toc small { display: block; margin-top: .3rem; } progress { width: 100%; accent-color: var(--cm-primary); } .review-originals h3 { margin-top: 0; font-size: 1rem; } .review-originals p { overflow-wrap: anywhere; font-size: .85rem; }
.review-overview { border-bottom: 1px solid var(--cm-border-light); padding-bottom: 1.5rem; } .review-overview h2 { font-size: 1.5rem; } .review-boundary { color: var(--cm-text-secondary); line-height: 1.7; } .review-legend { display: flex; flex-wrap: wrap; gap: .5rem; font-size: .75rem; } .review-legend span { padding: .3rem .5rem; background: var(--cm-bg-secondary); border: 1px solid var(--cm-border-light); border-radius: 4px; }
.review-section { padding: 2rem 0; border-bottom: 1px solid var(--cm-border-light); } .review-section, .review-block, .review-quick article { scroll-margin-top: 110px; outline: none; } .review-section h2 { font-size: 1.4rem; margin: .5rem 0 1.5rem; } .review-block { margin-bottom: 1.3rem; } .block-kind { font-size: .7rem; display: block; margin-bottom: .3rem; } .quote { border-left: 3px solid var(--cm-border-medium); padding: .5rem 1rem; } .inference { border-left: 3px dashed var(--cm-border-medium); padding-left: 1rem; } .missing { color: var(--cm-text-secondary); font-style: italic; } .term-link { border: 0; border-bottom: 1px dashed var(--cm-primary); color: var(--cm-primary); background: transparent; font-size: .8rem; padding: .2rem; margin: .2rem .4rem; }
.review-takeaways { background: var(--cm-bg-secondary); border-radius: 8px; padding: 1.2rem; margin: 1.5rem 0; } .review-takeaways h3 { margin-top: 0; font-size: 1rem; } .takeaway-link { padding: 0; border: 0; text-align: left; background: transparent; display: block; } .review-takeaways>div { margin: .7rem 0; } .review-erratum { border: 1px dashed var(--cm-border-medium); padding: 1rem; margin: 1rem 0; } .review-erratum button { margin: .3rem; } .review-highlight { outline: 2px solid var(--cm-primary); outline-offset: 5px; }
.original-thumbnail { display: block; width: 100%; padding: .4rem; margin: .7rem 0; text-align: left; } .original-thumbnail img { width: 100%; } .original-thumbnail span { font-size: .8rem; } .original-full { display: block; width: 100%; height: auto; } .source-text { white-space: pre-wrap; } .original-controls { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; } pre { padding: 1rem; background: var(--cm-bg-secondary); overflow: auto; } .table-scroll { overflow: auto; } table { border-collapse: collapse; width: 100%; } td, th { text-align: left; border: 1px solid var(--cm-border-light); padding: .5rem; } .quick-filters { display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 0; } .review-quick details { margin-bottom: 1rem; } .review-quick summary { cursor: pointer; padding: .7rem 0; font-weight: 600; } .review-quick article { padding: 1rem; border-bottom: 1px solid var(--cm-border-light); } .review-quick h4 { margin: .5rem 0; } .mobile-nav { display: none; }
@media(max-width:1100px) { .review-layout { grid-template-columns: 180px minmax(0,1fr); } .review-originals { display: none; } }
@media(max-width:700px) { main { padding: .8rem; } .review-toolbar { padding: .6rem; gap: .5rem; } .review-toolbar h1 { flex: 1; } .review-search { order: 5; flex-basis: 100%; } .review-layout, .quick-layout { display: block; } .review-toc { display: none; } .review-toc.is-open { display: block; position: static; max-height: 50vh; margin-bottom: 1rem; } .mobile-nav { display: block; } .review-setup { padding: 1rem; } .review-section, .review-block, .review-quick article { scroll-margin-top: 150px; } }
@media(prefers-reduced-motion:reduce) { * { scroll-behavior: auto !important; transition: none !important; } }
</style>
