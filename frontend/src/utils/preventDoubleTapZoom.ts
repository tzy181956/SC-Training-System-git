let lastTouchEnd = 0

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

export function installPreventDoubleTapZoom() {
  document.addEventListener(
    'touchend',
    (event) => {
      if (isEditableTarget(event.target)) return

      const now = Date.now()
      if (now - lastTouchEnd <= 300) {
        event.preventDefault()
      }
      lastTouchEnd = now
    },
    { passive: false },
  )
}
