import './assets/base.css'
import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'

import { router } from '@/app/router'
import { installI18n } from '@/app/providers/i18n'
import { installLogger } from '@/app/providers/logger'
import { installQuery } from '@/app/providers/query'
import { installTheme } from '@/app/providers/theme'

const app = createApp(App)

installTheme(app)
installLogger(app)
installI18n(app)
installQuery(app)
app.use(router)

app.mount('#app')
