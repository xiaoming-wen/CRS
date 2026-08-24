/**
 * 将竞赛 contact_name + contact_phone（自由文本）解析为侧栏可展示的多行联系人信息。
 * 支持超管在「联系方式」中按「标签：内容」填写，例如：
 *   电话：14790340147 邮箱：a@b.com QQ群：1081238089
 */

const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i
/** 11 位手机或带区号固话等 */
const PHONE_RE = /(?:\+?86[-\s]?)?1[3-9]\d{9}|(?:0\d{2,3}[-\s]?)?\d{7,8}/

const LABEL_ALIASES = [
  { re: /^(电话|手机|手机号|联系方式|Tel)$/i, label: '电话', key: 'phone' },
  { re: /^(邮箱|Email|E-mail|邮件)$/i, label: '邮箱', key: 'email' },
  { re: /^(QQ群|qq群)$/i, label: 'QQ群', key: 'qq_group' },
  { re: /^(QQ号|QQ)$/i, label: 'QQ', key: 'qq' },
  { re: /^(微信|WeChat|微信号)$/i, label: '微信', key: 'wechat' },
  { re: /^(钉钉)$/i, label: '钉钉', key: 'dingtalk' }
]

const SPLIT_LABEL_RE =
  /(电话|手机|手机号|联系方式|Tel|邮箱|Email|E-mail|邮件|QQ群|qq群|QQ号|QQ|微信|WeChat|微信号|钉钉)[:：]/gi

function normalizeLabel (raw) {
  const s = String(raw || '').trim()
  for (let i = 0; i < LABEL_ALIASES.length; i++) {
    const a = LABEL_ALIASES[i]
    if (a.re.test(s)) return { label: a.label, key: a.key }
  }
  return { label: s || '其他', key: `other_${s || 'x'}` }
}

function cleanValue (v) {
  return String(v || '')
    .replace(/^[\s,，;；、|/]+/, '')
    .replace(/[\s,，;；、|/]+$/, '')
    .trim()
}

/**
 * 按「标签：」切分自由文本为条目。
 * @param {string} text
 * @returns {{ label: string, key: string, value: string }[]}
 */
function splitByLabels (text) {
  const src = String(text || '').trim()
  if (!src) return []

  const matches = []
  let m
  const re = new RegExp(SPLIT_LABEL_RE.source, 'gi')
  while ((m = re.exec(src)) !== null) {
    matches.push({ rawLabel: m[1], index: m.index, end: m.index + m[0].length })
  }

  if (!matches.length) return []

  const items = []
  // 第一个标签前的残留文本
  if (matches[0].index > 0) {
    const head = cleanValue(src.slice(0, matches[0].index))
    if (head) items.push({ rawLabel: '', value: head, unlabeled: true })
  }

  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].end
    const end = i + 1 < matches.length ? matches[i + 1].index : src.length
    const value = cleanValue(src.slice(start, end))
    if (!value) continue
    items.push({ rawLabel: matches[i].rawLabel, value, unlabeled: false })
  }
  return items
}

function pushRow (rows, seen, key, label, value) {
  const v = cleanValue(value)
  if (!v) return
  const dedupeKey = `${label}::${v}`
  if (seen.has(dedupeKey)) return
  seen.add(dedupeKey)
  // 同 key 可多行（少见）；key 加序号保证 Vue key 唯一
  const n = rows.filter(r => r.key === key || String(r.key).startsWith(`${key}__`)).length
  rows.push({
    key: n === 0 ? key : `${key}__${n}`,
    label,
    value: v
  })
}

function classifyUnlabeled (chunk) {
  const t = cleanValue(chunk)
  if (!t) return null
  if (EMAIL_RE.test(t) && t.replace(EMAIL_RE, '').trim() === '') {
    return { key: 'email', label: '邮箱', value: t.match(EMAIL_RE)[0] }
  }
  const emailIn = t.match(EMAIL_RE)
  if (emailIn) {
    return { key: 'email', label: '邮箱', value: emailIn[0] }
  }
  if (PHONE_RE.test(t) && t.replace(PHONE_RE, '').replace(/[\s-]/g, '') === '') {
    return { key: 'phone', label: '电话', value: t.match(PHONE_RE)[0] }
  }
  if (/^\d{5,12}$/.test(t)) {
    // 纯数字群号等：偏短当电话，偏长当 QQ 群（启发式）
    if (t.length >= 6 && t.length <= 12 && !/^1[3-9]\d{9}$/.test(t)) {
      return { key: 'qq_group', label: 'QQ群', value: t }
    }
    return { key: 'phone', label: '电话', value: t }
  }
  return { key: 'other', label: '其他', value: t }
}

/**
 * @param {{ contact_name?: *, contact_phone?: *, contact_tel?: *, phone?: *, hotline?: *, contact?: * }} c
 * @returns {{ key: string, label: string, value: string }[]}
 */
export function parseCompetitionContactRows (c) {
  const rows = []
  const seen = new Set()
  const src = c && typeof c === 'object' ? c : {}

  const name = src.contact_name != null ? String(src.contact_name).trim() : ''
  if (name) pushRow(rows, seen, 'name', '联系人', name)

  let phoneRaw = src.contact_phone != null ? String(src.contact_phone).trim() : ''
  if (!phoneRaw) {
    const legacy = src.contact_tel || src.phone || src.hotline || src.contact
    if (legacy != null && String(legacy).trim() !== '') {
      phoneRaw = String(legacy).trim()
    }
  }
  if (!phoneRaw) return rows

  const labeled = splitByLabels(phoneRaw)
  if (labeled.length) {
    labeled.forEach((item) => {
      if (item.unlabeled) {
        const hit = classifyUnlabeled(item.value)
        if (hit) pushRow(rows, seen, hit.key, hit.label, hit.value)
        return
      }
      const meta = normalizeLabel(item.rawLabel)
      pushRow(rows, seen, meta.key, meta.label, item.value)
    })
    return rows
  }

  // 无标签：按邮箱 / 电话启发式拆分
  let rest = phoneRaw
  const emails = rest.match(new RegExp(EMAIL_RE.source, 'gi')) || []
  emails.forEach((em) => {
    pushRow(rows, seen, 'email', '邮箱', em)
    rest = rest.replace(em, ' ')
  })
  rest = cleanValue(rest.replace(/^(电话|手机|联系方式|微信)[:：\s]*/i, ''))
  if (rest) {
    const phoneHit = rest.match(PHONE_RE)
    if (phoneHit) {
      pushRow(rows, seen, 'phone', '电话', phoneHit[0])
      rest = cleanValue(rest.replace(phoneHit[0], ' '))
    }
  }
  if (rest) {
    const hit = classifyUnlabeled(rest)
    if (hit) pushRow(rows, seen, hit.key, hit.label, hit.value)
  }

  return rows
}
