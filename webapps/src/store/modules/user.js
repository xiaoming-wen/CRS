import Vue from 'vue'
import { ACCESS_TOKEN } from '@/store/mutation-types'

/** 独立工程不依赖主站登录；Logout 供 request 拦截器清理本地 token */
const user = {
  state: {
    token: '',
    name: '',
    welcome: '',
    avatar: '',
    roles: [],
    info: {}
  },
  mutations: {
    SET_TOKEN: (state, token) => {
      state.token = token
    },
    SET_NAME: (state, { name, welcome }) => {
      state.name = name
      state.welcome = welcome
    },
    SET_AVATAR: (state, avatar) => {
      state.avatar = avatar
    },
    SET_ROLES: (state, roles) => {
      state.roles = roles
    },
    SET_INFO: (state, info) => {
      state.info = info
    }
  },
  actions: {
    Logout ({ commit }) {
      return Promise.resolve().finally(() => {
        commit('SET_TOKEN', '')
        commit('SET_ROLES', [])
        commit('SET_NAME', { name: '', welcome: '' })
        commit('SET_AVATAR', '')
        commit('SET_INFO', {})
        Vue.ls.remove(ACCESS_TOKEN)
        localStorage.removeItem('access_token')
        Vue.ls.remove('access_token')
        localStorage.removeItem('user_info')
      })
    }
  }
}

export default user
