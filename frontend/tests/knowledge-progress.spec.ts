import { expect, test } from '@playwright/test'
import { mkdir } from 'node:fs/promises'

const documentId = '11111111-1111-4111-8111-111111111111'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('locale', 'zh-CN')
    const originalFetch = window.fetch.bind(window)
    const state = window as unknown as { ragController: ReadableStreamDefaultController<Uint8Array>; ragCancelled: boolean }
    window.fetch = async (input, init) => {
      if (String(input).includes('/api/v1/rag/ask/stream')) {
        const stream = new ReadableStream<Uint8Array>({ start(controller) {
          state.ragController = controller
          init?.signal?.addEventListener('abort', () => { state.ragCancelled = true; controller.error(new DOMException('Aborted', 'AbortError')) }, { once: true })
        } })
        return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } })
      }
      return originalFetch(input, init)
    }
  })
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test', user: { id: 1, username: 'test', nickname: '学生' } } })
    if (path.endsWith('/documents')) return route.fulfill({ json: { documents: [{ id: documentId, original_name: 'Synthetic source.pdf', status: 'succeeded', updated_at: '2026-11-13T10:00:00Z' }], total: 1 } })
    return route.fulfill({ status: 404, json: { detail: 'not found' } })
  })
})

async function send(page: import('@playwright/test').Page, event: string, data: unknown, close = false) {
  await page.evaluate(({ event, data, close }) => {
    const controller = (window as unknown as { ragController: ReadableStreamDefaultController<Uint8Array> }).ragController
    const bytes = new TextEncoder().encode(`event: ${event}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`)
    // Deliberately split every byte to cover fragmented frames and UTF-8 characters.
    for (const byte of bytes) controller.enqueue(new Uint8Array([byte]))
    if (close) controller.close()
  }, { event, data, close })
}

async function start(page: import('@playwright/test').Page) {
  await page.goto(`/knowledge-ask?documentId=${documentId}`)
  await page.getByRole('textbox').fill('这份资料讲了什么？')
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.locator('.task-activity')).toContainText('正在连接知识库')
}

test('shows server phases and elapsed time, then displays validated answer', async ({ page }) => {
  await start(page)
  const activity = page.locator('.task-activity')
  await expect(activity).toContainText('已用时 0:01', { timeout: 4000 })
  // Time passing must never advance the operation label on its own.
  await expect(activity).toContainText('正在连接知识库')
  for (const [phase, label] of [['authorizing', '正在确认所选资料'], ['retrieving', '正在检索相关资料'], ['generating', '正在依据资料生成回答'], ['validating', '正在核对回答与引用']]) {
    await send(page, 'phase', { phase }); await expect(activity).toContainText(label)
  }
  await mkdir('/tmp/coursemind-review-qa', { recursive: true })
  await page.screenshot({ path: '/tmp/coursemind-review-qa/knowledge-progress.png', fullPage: true })
  await send(page, 'result', { answer: '这是一份合成测试资料。[S1]', sources: [], model: 'fake', insufficient_context: false }, true)
  await expect(activity).toBeHidden()
  await expect(page.locator('.answer-text')).toContainText('这是一份合成测试资料。')
  await expect(page.getByRole('button', { name: '提问', exact: true })).toBeEnabled()
})

test('error or interrupted stream stops the activity and allows retry', async ({ page }) => {
  await start(page)
  await send(page, 'phase', { phase: 'generating' })
  await send(page, 'error', { status: 503, message: 'AI service temporarily unavailable' }, true)
  await expect(page.locator('.task-activity')).toBeHidden()
  await expect(page.locator('.answer-card[role=alert]')).toContainText('本次问答已停止')
  await page.getByRole('button', { name: '提问', exact: true }).click()
  await expect(page.locator('.task-activity')).toBeVisible()
  await page.evaluate(() => (window as unknown as { ragController: ReadableStreamDefaultController<Uint8Array> }).ragController.close())
  await expect(page.locator('.task-activity')).toBeHidden()
  await expect(page.locator('.answer-card[role=alert]')).toContainText('本次问答已停止')
})

test('leaving the page aborts the active request', async ({ page }) => {
  await start(page)
  await send(page, 'phase', { phase: 'retrieving' })
  await page.getByRole('button', { name: '返回', exact: false }).click()
  await expect.poll(() => page.evaluate(() => (window as unknown as { ragCancelled: boolean }).ragCancelled)).toBe(true)
})

test('activity fits a narrow screen and follows the English locale', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/knowledge-ask?documentId=${documentId}`)
  await page.locator('.locale-switcher').click()
  await page.getByRole('option', { name: 'English', exact: true }).click()
  await page.getByRole('textbox').fill('What is in this material?')
  await page.getByRole('button', { name: 'Ask', exact: true }).click()
  await expect(page.locator('.task-activity')).toContainText('connecting to the knowledge base')
  await send(page, 'phase', { phase: 'generating' })
  await expect(page.locator('.task-activity')).toContainText('generating a source-grounded answer')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await send(page, 'result', { answer: 'Insufficient source material.', sources: [], model: null, insufficient_context: true }, true)
  await expect(page.locator('.task-activity')).toBeHidden()
})
