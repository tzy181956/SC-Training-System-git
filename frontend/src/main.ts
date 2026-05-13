import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import pinia from './stores/pinia'
import './styles/tokens.css'
import './styles/main.css'
import { installPreventDoubleTapZoom } from './utils/preventDoubleTapZoom'

installPreventDoubleTapZoom()

createApp(App).use(pinia).use(router).mount('#app')
