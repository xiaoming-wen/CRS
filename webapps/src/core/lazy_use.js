import Vue from 'vue'
import VueStorage from 'vue-ls'
import config from '@/config/defaultSettings'
import '@/core/lazy_lib/components_use'

Vue.use(VueStorage, config.storageOptions)
