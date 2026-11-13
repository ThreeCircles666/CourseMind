import { expect, test } from '@playwright/test'
import { readFile, mkdir } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import type { CoursewareReview } from '../src/api/review'

const docId = '11111111-1111-4111-8111-111111111111'
const reviewId = '22222222-2222-4222-8222-222222222222'
const evidence = [{ page: 1, quote: 'y = 2x + 1', origin: 'text' as const }]
const fixture: CoursewareReview = {
  id: reviewId, document_ids: [docId], language: 'zh-CN', use_vision: false, status: 'ready',
  created_at: '2026-11-13T10:00:00Z', completed_pages: 2, error: null, duplicates: [], reviewed_sections: [],
  documents: [{ id: docId, name: 'Linear relations.pdf', pages: [
    { number: 1, text: 'y = 2x + 1; 2 + 2 = 5', has_image: true, read_mode: 'text' },
    { number: 2, text: 'Example: x = 3; y = 7', has_image: true, read_mode: 'text' },
  ] }],
  sections: [{ id: 'linear', document_id: docId, title: '线性关系 (Linear relation)', pages: [1, 2],
    blocks: [
      { kind: 'quote', text: 'y = 2x + 1', rows: [], evidence },
      { kind: 'explanation', text: '斜率 (Slope) 为 2，截距为 1。公式为 $y=2x+1$。', rows: [], evidence },
      { kind: 'formula', text: 'y = 2x + 1', rows: [], evidence },
      { kind: 'table', text: '课件数据', rows: [['x', 'y'], ['3', '7']], evidence },
      { kind: 'code', text: '<script>window.sourceExecuted=true</script>', rows: [], evidence },
      { kind: 'missing', text: '课件没有给出其他关系。', rows: [], evidence: [] },
    ],
    takeaways: [{ kind: 'formula', name: '线性公式', text: '线性公式：$y=2x+1$。', evidence }],
    quick_reference: [{ kind: 'formula', name: '线性公式', text: '$y=2x+1$', evidence }],
    demos: [
      { kind: 'linear', title: '参数探索', a: 2, b: 1, minimum: 0, maximum: 10, steps: [], illustrative: true, evidence },
      { kind: 'steps', title: '课件例题', a: 1, b: 0, minimum: 0, maximum: 10, steps: ['代入 $x=3$。', '得到 $y=7$。'], illustrative: false, evidence },
    ],
    errata: [{ id: 'arithmetic', status: 'candidate', original: '2 + 2 = 5', correction: '2 + 2 = 4', reason: '显式四则运算复算。', impact: '需确认后续结论。', evidence: [{ page: 1, quote: '2 + 2 = 5' }] }],
  }],
}
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXYQAAAAASUVORK5CYII=', 'base64')

test.beforeEach(async ({ page }) => {
  const state = structuredClone(fixture)
  await page.addInitScript(() => localStorage.setItem('locale', 'zh-CN'))
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test', user: { id: 1, username: 'test', nickname: '学生' } } })
    if (path.endsWith('/documents')) return route.fulfill({ json: { documents: [{ id: docId, original_name: 'Linear relations.pdf', status: 'succeeded' }], total: 1 } })
    if (path.endsWith('/image')) return route.fulfill({ contentType: 'image/png', body: png })
    if (path.endsWith('/state')) {
      const patch = route.request().postDataJSON()
      if (patch.reviewed_sections) state.reviewed_sections = patch.reviewed_sections
      if (patch.erratum_id) state.sections[0].errata[0].status = patch.decision
      return route.fulfill({ json: state })
    }
    if (path.endsWith('/reviews') && method === 'GET') return route.fulfill({ json: [state] })
    if (path.endsWith('/reviews') && method === 'POST') return route.fulfill({ status: 202, json: state })
    if (path.endsWith(`/${reviewId}`)) return route.fulfill({ json: state })
    return route.fulfill({ status: 404, json: { detail: 'not found' } })
  })
})

test('desktop review: sources, formulas, demos, state, search and offline export', async ({ page, context }, testInfo) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto(`/review?review=${reviewId}`)
  await expect(page.locator('.review-section')).toHaveCount(1)
  await expect(page.locator('.katex').first()).toBeVisible()
  await expect(page.locator('.review-block.code')).toContainText('<script>')
  expect(await page.evaluate(() => (window as unknown as { sourceExecuted?: boolean }).sourceExecuted)).toBeUndefined()
  const source = page.locator('.source-tag').first()
  await source.focus(); await expect(page.locator('.el-popover:visible')).toContainText('y = 2x + 1')
  await source.click(); await expect(page.locator('.original-full')).toBeVisible()
  await page.locator('.original-controls button').nth(1).click()
  await expect(page.locator('.el-dialog__title')).toContainText('p2')
  await page.locator('.original-controls button').last().click()
  await page.getByRole('button', { name: '标记为已复习', exact: true }).click()
  await expect(page.getByRole('button', { name: '已复习 ✓', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: '核对后确认', exact: true }).click()
  await expect(page.locator('.review-erratum strong')).toContainText('用户已确认')
  const slider = page.locator('.review-demo input[type=range]')
  await slider.fill('5'); await slider.dispatchEvent('input')
  await expect(page.locator('.review-demo output')).toContainText('11.0000')
  const steps = page.locator('.review-demo').nth(1)
  await steps.getByRole('button', { name: '下一步 / 下一页' }).click()
  await expect(steps).toContainText('2 / 2')
  const search = page.getByRole('combobox', { name: /搜索术语/ })
  await search.fill('线性公式'); await search.press('ArrowDown'); await search.press('Enter')
  await expect(page.locator('.review-quick')).toBeVisible()
  await page.locator('.review-quick').getByRole('button', { name: '回到讲解', exact: true }).click()
  await expect(page.locator('.review-section')).toBeVisible()
  await page.evaluate(() => scrollTo(0, 0))
  await mkdir('/tmp/coursemind-review-qa', { recursive: true })
  await page.screenshot({ path: '/tmp/coursemind-review-qa/desktop.png', fullPage: false })
  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载离线网页', exact: true }).click()
  const download = await downloadEvent
  const path = testInfo.outputPath('review.html'); await download.saveAs(path)
  const html = await readFile(path, 'utf8')
  expect(html).toContain('data:font/woff2;base64,')
  expect(html).not.toMatch(/src:url\((?!data:)/)
  const offline = await context.newPage(); const requests: string[] = []
  offline.on('pageerror', e => errors.push(e.message))
  offline.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()) })
  await context.setOffline(true)
  await offline.goto(pathToFileURL(path).href)
  await expect(offline.locator('#summary article')).toHaveCount(1)
  await expect(offline.locator('.katex').first()).toBeVisible()
  await offline.locator('[data-page]').first().click(); await expect(offline.locator('#original')).toBeVisible()
  await offline.locator('#back').click()
  await offline.locator('[data-view=quick]').first().click(); await expect(offline.locator('#quick')).toBeVisible()
  await offline.locator('.quick-entry [data-go]').click()
  await offline.locator('[data-reviewed]').click(); await expect(offline.locator('#progress')).toHaveAttribute('value', '0')
  await offline.locator('.demo[data-kind=linear] input').fill('6'); await offline.locator('.demo[data-kind=linear] input').dispatchEvent('input')
  await expect(offline.locator('.demo output')).toContainText('13.0000')
  await offline.reload(); await expect(offline.locator('#progress')).toHaveAttribute('value', '0')
  expect(requests).toEqual([]); expect(errors).toEqual([])
})

test('narrow layout, navigation and English locale', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/review?review=${reviewId}`)
  await expect(page.locator('.review-section')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
  await page.getByRole('button', { name: '目录', exact: true }).click()
  await expect(page.locator('.review-toc')).toBeVisible()
  await page.locator('.review-toc button').first().click()
  await expect(page.locator('.review-toc')).toBeHidden()
  await page.locator('.source-tag').first().click(); await expect(page.locator('.el-dialog')).toBeVisible()
  await page.keyboard.press('Escape'); await expect(page.locator('.el-dialog')).toBeHidden()
  await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: '/tmp/coursemind-review-qa/mobile.png' })
  await page.locator('.locale-switcher').click(); await page.getByRole('option', { name: 'English', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Courseware Review', exact: true })).toBeVisible()
})


test('canvas binds source IDs rather than cycling retrieved pages', async ({ page }) => {
  await page.route('**/api/v1/rag/ask', route => route.fulfill({ json: {
    answer: '1. 第一项：来自第二个来源 [S2]\n2. 第二项：来自第七个来源 [S7]\n3. 无匹配项：不应伪造来源 [S99]',
    sources: [
      { source_id: 'S7', document_id: docId, file_name: 'Linear relations.pdf', page_number: 70, excerpt: 'Source seven' },
      { source_id: 'S2', document_id: docId, file_name: 'Linear relations.pdf', page_number: 20, excerpt: 'Source two' },
    ], insufficient_context: false, model: 'fake',
  } }))
  await page.goto(`/canvas?documentId=${docId}`)
  await page.getByRole('button', { name: '生成学习画布', exact: true }).click()
  const first = page.locator('.card-title').filter({ hasText: '第一项' }).locator('..')
  const second = page.locator('.card-title').filter({ hasText: '第二项' }).locator('..')
  const unknown = page.locator('.card-title').filter({ hasText: '无匹配项' }).locator('..')
  await expect(first.locator('.card-source')).toContainText('第 20 页')
  await expect(second.locator('.card-source')).toContainText('第 70 页')
  await expect(unknown.locator('.card-source')).not.toContainText('页')
})


test('restores active review and reports real stages, elapsed time, failure and retry', async ({ page }) => {
  const state = structuredClone(fixture)
  state.status = 'processing'; state.phase = 'summarizing'; state.completed_pages = 4; state.total_pages = 28
  state.current_pages = [5, 6, 7, 8]; state.current_document = docId; state.sections = []
  state.created_at = new Date(Date.now() - 65000).toISOString()
  let submissions = 0
  await page.route('**/api/v1/reviews**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/reviews') && route.request().method() === 'POST') {
      submissions++; state.status = 'queued'; state.phase = 'queued'; state.error = null; state.error_code = undefined
      return route.fulfill({ status: 202, json: state })
    }
    return route.fulfill({ json: path.endsWith('/reviews') ? [state] : state })
  })
  await page.goto('/review')
  const activity = page.locator('.review-activity')
  await expect(activity).toBeVisible()
  await expect(activity).toContainText('正在整理讲解与速查')
  await expect(activity).toContainText('p5, p6, p7, p8')
  await expect(activity).toContainText(/已用时 1:\d{2}/)
  await expect(page.locator('.review-status')).toContainText('已完成 4 / 28 页')
  await mkdir('/tmp/coursemind-review-qa', { recursive: true })
  await page.screenshot({ path: '/tmp/coursemind-review-qa/progress.png' })
  state.phase = 'retrying'
  await expect(activity).toContainText('正在修正生成结果并重试', { timeout: 8000 })
  state.phase = 'validating'
  await expect(activity).toContainText('正在核对页码与原文引用', { timeout: 8000 })
  state.status = 'failed'; state.phase = 'failed'; state.error = 'Validation failed'; state.error_code = 'output_validation'
  await expect(page.locator('.review-status')).toContainText('本次已停止', { timeout: 8000 })
  await expect(activity).toBeHidden()
  await page.getByRole('button', { name: '重新生成', exact: true }).click()
  await expect(activity).toContainText('任务已排队，等待开始')
  expect(submissions).toBe(1)
})
