type DangerousActionOptions = {
  title: string
  impactLines: string[]
  recommendation?: string
  confirmationKeyword?: string | null
}

function buildMessage(options: DangerousActionOptions) {
  const sections = [
    options.title,
    '',
    '影响范围：',
    ...options.impactLines.map((line) => `- ${line}`),
    '',
    options.recommendation || '建议先确认系统已生成自动备份，再继续。',
  ]
  return sections.join('\n')
}

export function confirmDangerousAction(options: DangerousActionOptions) {
  const message = buildMessage(options)
  const confirmed = window.confirm(`${message}\n\n确认继续执行吗？`)
  if (!confirmed) return false

  if (!options.confirmationKeyword) return true

  const input = window.prompt(`${message}\n\n这是高危操作，请输入确认词：${options.confirmationKeyword}`, '')
  if ((input || '').trim() === options.confirmationKeyword) return true

  window.alert('确认词不匹配，未执行任何改动。')
  return false
}
