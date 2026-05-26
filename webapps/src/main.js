import 'core-js/stable'
import 'regenerator-runtime/runtime'

import Vue from 'vue'
import { Modal } from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import store from './store'
import { VueAxios } from './utils/request'
import bootstrap from './core/bootstrap'
import './core/lazy_use'
import './permission'
import Dialog from './components/Dialog'

Vue.config.productionTip = false
Vue.use(VueAxios)
Vue.use(Dialog)
Vue.prototype.$modal = Modal

new Vue({
  router,
  store,
  created: bootstrap,
  render: h => h(App)
}).$mount('#app')
