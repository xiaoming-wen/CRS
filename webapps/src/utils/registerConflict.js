/**
 * 主站 /v1/auth/register 与竞赛 alt-identity/register 注册失败时的文案解析与冲突弹窗。
 */

export function extractRegisterError (err) {
  if (!err) return ''
  const r = err.response
  if (r && r.data) {
    const d = r.data
    if (typeof d.detail === 'string') return d.detail
    if (Array.isArray(d.detail)) {
      return d.detail
        .map(x => {
          if (!x || typeof x !== 'object') return ''
          return x.msg || x.message || ''
        })
        .filter(Boolean)
        .join('；')
    }
    if (typeof d.message === 'string') return d.message
    if (typeof d.msg === 'string') return d.msg
  }
  return err.message || ''
}

function formatConflictContent (msg, status) {
  const m = (msg || '').trim()
  const userMention = /用户名|username/i.test(m) && /(已|exist|taken|duplicate|占用|注册|使用)/i.test(m)
  const phoneMention = /手机|电话|phone|mobile/i.test(m) && /(已|exist|taken|duplicate|占用|注册|使用)/i.test(m)
  const emailMention = /邮箱|邮件|e-?mail/i.test(m) && /(已|exist|taken|duplicate|占用|注册|使用)/i.test(m)
  if (userMention && phoneMention) {
    return '该用户名与手机号已被注册，请更换后重试。'
  }
  if (userMention && emailMention) {
    return '该用户名与邮箱已被注册，请更换后重试。'
  }
  if (userMention) {
    return '该用户名已被注册，请更换用户名后重试。'
  }
  if (phoneMention) {
    return '该手机号已被注册，请更换手机号后重试。'
  }
  if (emailMention) {
    return '该邮箱已被注册，请更换邮箱后重试。'
  }
  if (status === 409 || /unique|duplicate|constraint/i.test(m)) {
    return m || '注册信息与他人重复，请修改后重试。'
  }
  return m || '该用户名或手机号已被注册，请更换后重试。'
}

function isConflictMessage (msg) {
  const m = (msg || '').trim()
  if (!m) return false
  if (/已注册|已被使用|已存在|already exists|duplicate|unique constraint|占用|被占用/i.test(m)) return true
  if ((/用户名|手机|电话|邮箱|username|phone|mobile|email/i.test(m)) && (/已|exist|duplicate|taken|注册|使用/i.test(m))) return true
  return false
}

/**
 * @param {object} vm Vue 组件实例（需已挂载 $modal）
 * @param {*} err axios 错误对象或仅有 message 的 Error
 * @returns {boolean} 是否已弹出冲突弹窗（true 时调用方勿再弹通用错误）
 */
export function showRegisterConflictModal (vm, err) {
  const msg = extractRegisterError(err)
  const status = err && err.response && err.response.status
  if (status === 409 || isConflictMessage(msg)) {
    vm.$modal.warning({
      title: '注册提示',
      content: formatConflictContent(msg, status)
    })
    return true
  }
  return false
}
