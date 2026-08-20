import Vue from 'vue'
import axios from 'axios'
import store from '@/store'
import notification from 'ant-design-vue/es/notification'
import { VueAxios } from './axios'
import { ACCESS_TOKEN } from '@/store/mutation-types'
import { clearAltIdentityStorage, getStoredAltToken } from '@/api/altIdentity'
import { isCompetitionApiPath, resolveRequestBearer } from '@/utils/competitionRequestAuth'

// 创建 axios 实例
// 开发环境使用代理 /api，生产环境使用完整URL
// 根据API文档，Base URL: http://192.168.3.238:8000/api/v1
// 开发环境通过代理，baseURL 设置为 /api
// 生产环境直接使用完整URL
const baseURL = process.env.VUE_APP_API_BASE_URL || '/api'

// 调试日志
console.log('API BaseURL:', baseURL)
console.log('NODE_ENV:', process.env.NODE_ENV)
console.log('VUE_APP_API_BASE_URL:', process.env.VUE_APP_API_BASE_URL)

const service = axios.create({
    baseURL: baseURL, // api base_url: /api (开发环境代理) 或 http://192.168.3.238:8000/api (生产环境)
    timeout: 24000 // 请求超时时间,
})

// 验证 baseURL 是否正确设置
console.log('Axios instance baseURL:', service.defaults.baseURL)

const err = (error) => {
    if (error.response) {
        const data = error.response.data
        const token = localStorage.getItem('access_token') || Vue.ls.get('access_token')

        if (error.response.status === 403) {
            notification.error({
                message: '权限不足',
                description: data.detail || '您没有权限访问此资源'
            })
        }

        // 处理401未授权错误
        if (error.response.status === 401) {
            const errorDetail = data.detail || ''
            const reqUrl = error.config && error.config.url
            const isCompetitionReq = isCompetitionApiPath(reqUrl)
            const usedAltAuth = error.config && error.config.__authSource === 'alt'
            const isAltIdentityRequired =
                typeof errorDetail === 'string' &&
                /alt-identity token|第二套|独立账号/i.test(errorDetail)

            if (isCompetitionReq && usedAltAuth) {
                clearAltIdentityStorage()
                notification.warning({
                    message: '竞赛账号登录已失效',
                    description: errorDetail || '请重新登录竞赛报名系统独立账号'
                })
            } else if (isCompetitionReq || isAltIdentityRequired) {
                // 竞赛接口缺 Alt 令牌：提示重新登录，勿清主站 JWT / 整页刷新
                notification.warning({
                    message: '请先登录竞赛账号',
                    description: errorDetail || '请使用竞赛报名系统独立账号登录后再试'
                })
            } else {
                if (errorDetail.includes('Could not validate credentials') && token) {
                    if (!error.config._retry) {
                        error.config._retry = true
                        notification.warning({
                            message: 'Token已过期',
                            description: '请重新登录或刷新token'
                        })
                    }
                } else {
                    notification.error({
                        message: '未授权',
                        description: errorDetail || '认证失败，请重新登录'
                    })
                }

                if (token) {
                    localStorage.removeItem('access_token')
                    Vue.ls.remove('access_token')
                    store.dispatch('Logout').then(() => {
                        setTimeout(() => {
                            window.location.reload()
                        }, 1500)
                    })
                }
            }
        }
    }
    return Promise.reject(error)
}

// request interceptor
// login 等接口 url 为 /v1/...，baseURL 为 /api → 最终 /api/v1/...；勿在 url 上再拼 /api（会变成 /api/api/v1/...）
service.interceptors.request.use(config => {
    const reqUrl = config.url || ''
    const getMainToken = () =>
        localStorage.getItem('access_token') || Vue.ls.get('access_token') || Vue.ls.get(ACCESS_TOKEN)
    const { token: bearer, source: authSource } = resolveRequestBearer(reqUrl, getMainToken)

    if (bearer) {
        config.headers['Authorization'] = `Bearer ${bearer}`
        config.__authSource = authSource
    }

    // 对于 FormData，确保正确处理
    if (config.data instanceof FormData) {
        // 重要：对于 FormData，axios 会自动设置正确的 Content-Type: multipart/form-data; boundary=...
        // 如果手动设置了 Content-Type: multipart/form-data（没有 boundary），会导致问题
        // 所以我们需要删除手动设置的 Content-Type，让 axios 自动处理
        const contentType = config.headers['Content-Type'] || config.headers['content-type']
        if (contentType && contentType.includes('multipart/form-data') && !contentType.includes('boundary')) {
            // 如果手动设置了 multipart/form-data 但没有 boundary，删除它
            delete config.headers['Content-Type']
            delete config.headers['content-type']
            console.log('删除了不完整的 Content-Type，让 axios 自动设置')
        }

        // 验证 FormData 内容（仅用于调试）
        const entries = []
        for (const pair of config.data.entries()) {
            if (pair[0] === 'file') {
                entries.push(`${pair[0]}: [File对象: ${pair[1].name || '未知'}]`)
            } else {
                entries.push(`${pair[0]}: ${pair[1]}`)
            }
        }
        console.log('检测到 FormData，axios 将自动设置正确的 Content-Type')
        console.log('FormData 包含的字段:', entries)
        console.log('FormData 字段数量:', entries.length)
    }

    // 调试日志：显示请求配置
    console.log('Request URL:', config.url)
    console.log('Request Method:', config.method)
    if (config.data instanceof FormData) {
        console.log('Request is FormData')
        console.log('Request Headers (before axios processing):', JSON.stringify(config.headers, null, 2))
    }

    return config
}, err)

// response interceptor
service.interceptors.response.use((response) => {
    return response.data
}, err)

const installer = {
    vm: {},
    install (Vue) {
        Vue.use(VueAxios, service)
    }
}

export {
    installer as VueAxios,
    service as axios
}
