<script setup lang="ts">
import { PROJECT_CONTACT_LABEL, PROJECT_COPYRIGHT_TEXT } from '@/constants/projectMeta'

withDefaults(
  defineProps<{
    variant?: 'default' | 'compact'
  }>(),
  {
    variant: 'default',
  },
)
</script>

<template>
  <footer class="site-footer" :class="`site-footer--${variant}`">
    <div class="site-footer-contact">
      <span>{{ PROJECT_CONTACT_LABEL }}</span>
      <span class="site-footer-contact-slot" aria-hidden="true"></span>
    </div>
    <div class="site-footer-copyright">{{ PROJECT_COPYRIGHT_TEXT }}</div>
  </footer>
</template>

<style scoped>
.site-footer {
  width: 100%;
  border-top: 1px solid rgba(148, 163, 184, 0.38);
  color: var(--muted);
  font-size: 13px;
  line-height: 1.4;
}

.site-footer-contact,
.site-footer-copyright {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 7px 12px;
  text-align: center;
}

.site-footer-contact {
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.site-footer-contact-slot {
  display: inline-block;
  min-width: 8em;
  min-height: 1em;
}

.site-footer-copyright {
  color: var(--text);
  font-weight: 700;
}

.site-footer--compact {
  font-size: 12px;
}

.site-footer--compact .site-footer-contact,
.site-footer--compact .site-footer-copyright {
  padding: 4px 10px;
}

@media (max-width: 767px) {
  .site-footer-contact,
  .site-footer-copyright {
    justify-content: flex-start;
    text-align: left;
  }
}
</style>
