import katex from 'katex'

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]!))
}

export function mathHtml(text: string, formula = false): string {
  const render = (tex: string, displayMode: boolean) => katex.renderToString(tex, {
    displayMode, throwOnError: false, trust: false, strict: 'ignore', maxExpand: 100,
    maxSize: 20, output: 'htmlAndMathml',
  })
  if (formula) return render(text.replace(/^\$\$?|\$\$?$/g, ''), true)
  // Escape all prose; only KaTeX can emit markup. Source HTML never enters the DOM.
  const pattern = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)/g
  let output = '', cursor = 0
  for (const match of text.matchAll(pattern)) {
    output += escapeHtml(text.slice(cursor, match.index)).replace(/\n/g, '<br>')
    output += render(match[1] ?? match[2] ?? match[3] ?? match[4], Boolean(match[1] ?? match[3]))
    cursor = match.index! + match[0].length
  }
  return output + escapeHtml(text.slice(cursor)).replace(/\n/g, '<br>')
}
