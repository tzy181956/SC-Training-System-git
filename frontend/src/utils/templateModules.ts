export function moduleCodeFromOrder(sortOrder: number) {
  let value = Math.max(Number(sortOrder || 1), 1)
  let code = ''
  while (value > 0) {
    const remainder = (value - 1) % 26
    code = `${String.fromCharCode(65 + remainder)}${code}`
    value = Math.floor((value - 1) / 26)
  }
  return code
}

export function buildDisplayLabel(moduleCode: string) {
  return `模块 ${moduleCode}`
}

export function buildModulesFromItems(items: any[]) {
  const grouped = new Map<string | number, any>()
  const orderedModules: any[] = []

  ;[...(items || [])]
    .sort((left, right) => (left.sort_order || 0) - (right.sort_order || 0) || (left.id || 0) - (right.id || 0))
    .forEach((item) => {
      const moduleId = item.module_id ?? `fallback-${item.id ?? orderedModules.length + 1}`
      if (!grouped.has(moduleId)) {
        const moduleCode = item.module_code || moduleCodeFromOrder(orderedModules.length + 1)
        const moduleDraft = {
          id: typeof moduleId === 'number' ? moduleId : null,
          sort_order: orderedModules.length + 1,
          module_code: moduleCode,
          title: item.module_title || null,
          note: item.module_note || null,
          display_label: buildDisplayLabel(moduleCode),
          items: [],
        }
        grouped.set(moduleId, moduleDraft)
        orderedModules.push(moduleDraft)
      }
      const currentModule = grouped.get(moduleId)
      const displayIndex = currentModule.items.length + 1
      currentModule.items.push({
        ...item,
        module_code: item.module_code || currentModule.module_code,
        module_title: item.module_title || currentModule.title || null,
        display_index: item.display_index ?? displayIndex,
        display_code: item.display_code || `${currentModule.module_code}.${displayIndex}`,
      })
    })

  return orderedModules
}

export function resolveTemplateModules(template: any | null | undefined) {
  if (!template) return []
  if (Array.isArray(template.modules) && template.modules.length) {
    return [...template.modules]
      .sort((left, right) => (left.sort_order || 0) - (right.sort_order || 0) || (left.id || 0) - (right.id || 0))
      .map((module, moduleIndex) => {
        const moduleCode = module.module_code || moduleCodeFromOrder(module.sort_order || moduleIndex + 1)
        const moduleItems = [...(module.items || [])]
          .sort((left, right) => (left.sort_order || 0) - (right.sort_order || 0) || (left.id || 0) - (right.id || 0))
          .map((item, itemIndex) => ({
            ...item,
            module_id: item.module_id ?? module.id ?? null,
            module_code: item.module_code || moduleCode,
            module_title: item.module_title || module.title || null,
            display_index: item.display_index ?? itemIndex + 1,
            display_code: item.display_code || `${moduleCode}.${itemIndex + 1}`,
          }))
        return {
          ...module,
          module_code: moduleCode,
          display_label: module.display_label || buildDisplayLabel(moduleCode),
          items: moduleItems,
        }
      })
  }
  return buildModulesFromItems(template.items || [])
}
