export type TestMetricDirection = 'higher' | 'lower'

type MetricDirectionSource = {
  is_lower_better?: boolean | null
  direction?: TestMetricDirection | null
}

export type TestMetricDirectionMeta = {
  isLowerBetter: boolean
  direction: TestMetricDirection
  label: string
  hint: string
  shortLabel: string
}

export function getTestMetricDirectionMeta(source?: MetricDirectionSource | null): TestMetricDirectionMeta {
  const direction: TestMetricDirection =
    source?.direction === 'lower' || source?.is_lower_better ? 'lower' : 'higher'

  if (direction === 'lower') {
    return {
      isLowerBetter: true,
      direction,
      label: '低值优先',
      hint: '数值越小越好',
      shortLabel: '低值优先',
    }
  }

  return {
    isLowerBetter: false,
    direction,
    label: '高值优先',
    hint: '数值越大越好',
    shortLabel: '高值优先',
  }
}
