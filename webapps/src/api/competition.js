import { axios } from '@/utils/request'

/**
 * 竞赛报名系统接口封装（文档 §8：`GET|POST|PUT|DELETE /api/v1/competitions/...`）
 *
 * 鉴权：须由全局 axios 拦截器在请求头附带 **第二套 Alt JWT**（`POST /api/alt-identity/session` 签发），
 * 与主站 `access_token` **不可混用**。竞赛相关整型 ID（student_id / submitter_id / captain_id 等）
 * 语义均为 **alt_auth_users.id**（8 位数字，10000000–99999999），非主库 users.id。
 * 竞赛 ID（competition_id）同为 8 位数字，在竞赛表内唯一。
 * URL 以 `/v1/competitions/...` 书写；开发环境经 devServer 代理到 `/api`。
 */

// 8.1 创建竞赛（仅 super_admin）JSON — 仅文本字段；division_mode / qr_layout 等同 JSON 体
export function createCompetition (payload) {
  return axios({
    url: '/v1/competitions/',
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.1 创建竞赛 multipart — 文本字段 + 二维码（qr_code_image / qr_code_image_shared 共用；
// dual+separate 时用 qr_code_image_undergraduate、qr_code_image_vocational）；勿手动设 Content-Type
export function createCompetitionMultipart (formData) {
  return axios({
    url: '/v1/competitions/',
    method: 'post',
    data: formData
  })
}

// 8.2 发布竞赛（仅 super_admin）
export function publishCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/publish`,
    method: 'put',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.3 修改竞赛（仅 super_admin）JSON — 只传需改的文本字段（含 division_mode / qr_layout）
export function updateCompetition (competitionId, payload) {
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.3 修改竞赛 multipart — 仅提交需改的文本字段；二维码字段规则同 §8.1（未传文件不替换）
export function updateCompetitionMultipart (competitionId, formData) {
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'put',
    data: formData
  })
}

// 8.4 删除竞赛（仅 super_admin）
export function deleteCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}`,
    method: 'delete'
  })
}

// 8.5 锁定竞赛（停止报名；仅 super_admin）
export function lockCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/lock`,
    method: 'put',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 列表：文档未显式列出，但前端需要竞赛列表（GET competitions）
export function getCompetitions () {
  return axios({
    url: '/v1/competitions/',
    method: 'get'
  })
}

/** 初赛：可晋级决赛的队伍候选。options.work_track: works | software | hardware */
export function getPromotionCandidates (competitionId, options = {}) {
  const params = {}
  const track = options && options.work_track
  if (track) params.work_track = track
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/promotions/candidates`,
    method: 'get',
    params
  })
}

/** 初赛或决赛：晋级名单。options.work_track: works | software | hardware */
export function getCompetitionPromotions (competitionId, options = {}) {
  const params = {}
  const track = options && options.work_track
  if (track) params.work_track = track
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/promotions`,
    method: 'get',
    params
  })
}

/** 从初赛晋级队伍到决赛 */
export function createCompetitionPromotions (competitionId, payload) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/promotions`,
    method: 'post',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 撤销晋级 */
export function revokeCompetitionPromotion (competitionId, promotionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/promotions/${encodeURIComponent(promotionId)}`,
    method: 'delete'
  })
}

// 8.1.1 获取竞赛详情（单条；含 division_mode / qr_layout / qr_codes）
// 分享链接未登录时可匿名访问已发布竞赛，无需 Bearer
export function getCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}`,
    method: 'get'
  })
}

/** 竞赛二维码图（GET，一般为 image/png）；dual 分开展示时可传 division；已发布竞赛可匿名访问 */
export function getCompetitionQrCode (competitionId, options = {}) {
  const params = {
    // 避免浏览器对同一 URL 使用磁盘缓存，导致换图后仍显示旧二维码
    _t: (options && options.cacheBust) || Date.now()
  }
  const div = options && options.division
  if (div === 'undergraduate' || div === 'vocational') {
    params.division = div
  }
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/qr-code`,
    method: 'get',
    params,
    responseType: 'blob',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache'
    }
  })
}

/** 竞赛 Logo 图（GET）；已发布竞赛可匿名访问 */
export function getCompetitionLogo (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/logo`,
    method: 'get',
    params: {
      _t: (options && options.cacheBust) || Date.now()
    },
    responseType: 'blob',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache'
    }
  })
}

// 8.6 查看我报名的竞赛（当前 Alt 主体；响应 student_id 为 alt_auth_users.id，权限 VIEW_COMPETITIONS）
export function getMyCompetitionEnrollments () {
  return axios({
    url: '/v1/competitions/enrollments/me',
    method: 'get'
  })
}

// 8.10 查看个人参赛者花名册（dual 须传 division）
export function getCompetitionParticipantsIndividual (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/participants/individual`,
    method: 'get',
    params: buildCompetitionDivisionParams(options)
  })
}

// 8.11 查看组队参赛者花名册（dual 须传 division）
export function getCompetitionParticipantsTeams (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/participants/teams`,
    method: 'get',
    params: buildCompetitionDivisionParams(options)
  })
}

// 8.11.1 导出参赛对照表（按赛道拆成多份 Excel，打成 zip）
// options.scope: current | paired | both
export function exportCompetitionTeamsExcel (competitionId, options = {}) {
  const params = {
    ...buildCompetitionDivisionParams(options)
  }
  const scope = options && options.scope
  if (scope != null && String(scope).trim() !== '') {
    params.scope = String(scope).trim()
  }
  return axios({
    url: `/v1/competitions/${competitionId}/teams/export`,
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 管理员：Excel 导入决赛晋级名单（列：队伍ID，可选队伍名）。workTrack 限定赛道。 */
export function importCompetitionPromotionsExcel (competitionId, file, workTrack) {
  const fd = new FormData()
  fd.append('file', file)
  if (workTrack) fd.append('work_track', workTrack)
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/promotions/import`,
    method: 'post',
    data: fd,
    timeout: 120000
  })
}

/** 查看某队 5 题答案上传槽位 */
export function getCompetitionQuestionAnswersBoard (competitionId, teamId) {
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers`,
    method: 'get',
    params: { team_id: teamId }
  })
}

/** 管理员/专家：按队伍查看 5 题答案上传概览（作品列表） */
export function getCompetitionQuestionAnswersOverview (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers/overview`,
    method: 'get'
  })
}

/** 队员上传指定题号答案（覆盖同队同题） */
export function uploadCompetitionQuestionAnswer (competitionId, questionNo, formData) {
  return axios({
    url: `/v1/competitions/${competitionId}/questions/${questionNo}/answers/upload`,
    method: 'post',
    data: formData,
    timeout: 600000
  })
}

/** 下载单题答案文件 */
export function downloadCompetitionQuestionAnswer (competitionId, answerId) {
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers/${answerId}/download`,
    method: 'get',
    responseType: 'blob',
    timeout: 600000
  })
}

/** 删除单题答案（队员可删本队答案） */
export function deleteCompetitionQuestionAnswer (competitionId, answerId) {
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers/${answerId}`,
    method: 'delete'
  })
}

/** 正式上传作品：将本队已选答案全部提交（管理员/专家列表才可见） */
export function submitCompetitionQuestionAnswers (competitionId, teamId) {
  const fd = new FormData()
  fd.append('team_id', String(teamId))
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers/submit`,
    method: 'post',
    data: fd
  })
}

/**
 * 赛后导出答案 zip（按赛道）：
 * work_track=works|software|hardware
 * mode=by_team → 外层含「队伍ID.zip」；by_question → 外层含「第N题.zip」（作品赛道仅支持 by_team）
 * 下载文件名以后端 Content-Disposition 为准（赛道名称.zip）
 */
export function exportCompetitionQuestionAnswers (competitionId, mode, workTrack) {
  const params = { mode }
  if (workTrack) params.work_track = workTrack
  return axios({
    url: `/v1/competitions/${competitionId}/question-answers/export`,
    method: 'get',
    params,
    responseType: 'blob',
    timeout: 600000
  })
}

function trimStr (v) {
  if (v == null) return ''
  return String(v).trim()
}

/** dual 竞赛 Query：undergraduate | vocational；single 可省略 */
function buildCompetitionDivisionParams (options = {}) {
  const params = {}
  const div = options && options.division
  const s = div != null ? String(div).trim().toLowerCase() : ''
  if (s === 'undergraduate' || s === 'vocational' || s === 'default') {
    params.division = s
  }
  const rawPage = options && options.page
  const page = Number(rawPage)
  if (Number.isFinite(page) && page >= 1) {
    params.page = Math.floor(page)
  }
  const rawPageSize = options && options.page_size
  const pageSize = Number(rawPageSize)
  if (Number.isFinite(pageSize) && pageSize >= 1) {
    params.page_size = Math.floor(pageSize)
  }
  return params
}

// 8.7 报名参赛（学生：个人/队伍；dual 竞赛须传 division: undergraduate | vocational）
export function enrollCompetition (payload) {
  const raw = payload || {}
  const competitionId = Number(raw.competition_id)
  if (!Number.isFinite(competitionId) || competitionId <= 0) {
    return Promise.reject(new Error('竞赛 ID 无效'))
  }
  const body = { competition_id: competitionId }
  const teamRaw = raw.team_id
  const hasTeamIdKey = Object.prototype.hasOwnProperty.call(raw, 'team_id')
  if (teamRaw != null && teamRaw !== '') {
    const teamId = Number(teamRaw)
    if (Number.isFinite(teamId) && teamId > 0) {
      body.team_id = teamId
    }
  } else if (hasTeamIdKey && (teamRaw == null || teamRaw === '')) {
    body.team_id = null
  }
  const division = trimStr(raw.division)
  if (division === 'undergraduate' || division === 'vocational') {
    body.division = division
  }
  const workTrack = trimStr(raw.work_track)
  if (workTrack === 'works' || workTrack === 'software' || workTrack === 'hardware') {
    body.work_track = workTrack
  }
  const optionalKeys = ['student_no', 'real_name', 'college', 'grade', 'contact']
  for (const k of optionalKeys) {
    const s = trimStr(raw[k])
    if (s) body[k] = s
  }
  return axios({
    url: '/v1/competitions/enroll',
    method: 'post',
    data: body,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.8 退赛（学生；停止报名后仍可退赛，权限 ENROLL_COMPETITIONS）
// options.track: 'individual' | 'team' — 个人与组队两条报名均有效时必填
export function withdrawCompetition (competitionId, options = {}) {
  const params = {}
  const track = options && options.track
  if (track === 'individual' || track === 'team') {
    params.track = track
  }
  return axios({
    url: `/v1/competitions/${competitionId}/withdraw`,
    method: 'post',
    params
  })
}

// 8.9 查看竞赛队伍列表（dual 须传 division，每次只返回该组队伍）
export function getCompetitionTeams (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams`,
    method: 'get',
    params: buildCompetitionDivisionParams(options)
  })
}

// 8.12.0 查看单支队伍详情（队员/队长/建队老师；含校审 status）
export function getCompetitionTeam (teamId) {
  return axios({
    url: `/v1/competitions/teams/${encodeURIComponent(teamId)}`,
    method: 'get'
  })
}

// 8.9.1 按队名查找可加入队伍（精确匹配，忽略大小写）
export function lookupCompetitionTeamByName (competitionId, teamName) {
  const name = teamName != null ? String(teamName).trim() : ''
  if (!name) {
    return Promise.reject(new Error('队名不能为空'))
  }
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/teams/lookup`,
    method: 'get',
    params: { name }
  })
}

// 8.12 创建队伍（学生自建队长 / 指导老师组班；权限 MANAGE_TEAMS）
// 学生：{ competition_id, initial_member_ids?: null }
// 指导老师：{ competition_id, name?, captain_student_id?, initial_member_ids?: number[] }（队长或初始队员至少填一项）
export function createCompetitionTeam (payload) {
  return axios({
    url: '/v1/competitions/teams',
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.1 修改队名（队长或建队指导老师）
export function patchCompetitionTeam (teamId, payload) {
  return axios({
    url: `/v1/competitions/teams/${teamId}`,
    method: 'patch',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.2 邀请队员（队长或建队指导老师）；发出邀请，须对方同意后入队
export function inviteCompetitionTeamMember (teamId, studentOrPayload) {
  let data
  if (studentOrPayload != null && typeof studentOrPayload === 'object' && !Array.isArray(studentOrPayload)) {
    data = { ...studentOrPayload }
  } else if (typeof studentOrPayload === 'string' && !/^\d{8}$/.test(String(studentOrPayload).trim())) {
    data = { student: String(studentOrPayload).trim() }
  } else {
    data = { student_id: studentOrPayload }
  }
  return axios({
    url: `/v1/competitions/teams/${teamId}/invite`,
    method: 'post',
    data,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.2b 当前学生：待处理入队邀请
export function listMyTeamInvites (options = {}) {
  const params = {}
  if (options.status) params.status = options.status
  return axios({
    url: '/v1/competitions/team-invites/me',
    method: 'get',
    params
  })
}

// 8.12.2c 同意 / 拒绝入队邀请
export function respondTeamInvite (inviteId, action) {
  return axios({
    url: `/v1/competitions/team-invites/${encodeURIComponent(inviteId)}/respond`,
    method: 'post',
    data: { action },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.12.3 移除队员（队长或建队指导老师；不可踢队长）
export function removeCompetitionTeamMember (teamId, userId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/members/${userId}`,
    method: 'delete'
  })
}

// 8.13 申请加入队伍（学生；权限 MANAGE_TEAMS；须队长审核）
export function addTeamMember (teamId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/members`,
    method: 'post'
  })
}

// 8.13.1 查看入队申请（队长或建队指导老师）
export function listTeamJoinRequests (teamId, options = {}) {
  const params = {}
  if (options.status) params.status = options.status
  return axios({
    url: `/v1/competitions/teams/${teamId}/join-requests`,
    method: 'get',
    params
  })
}

// 8.13.2 审核入队申请（同意 / 拒绝）
export function reviewTeamJoinRequest (teamId, requestId, action) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/join-requests/${requestId}/review`,
    method: 'post',
    data: { action },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.14 队长转让（new_captain_id 须为队伍中成员的 alt_auth_users.id）
export function transferTeamCaptain (teamId, payload) {
  // payload: { team_id: int, new_captain_id: int }
  return axios({
    url: `/v1/competitions/teams/${teamId}/transfer-captain`,
    method: 'post',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.15 队长退队 / 队员退队（队长须先转让；权限 MANAGE_TEAMS）
export function leaveTeam (teamId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/leave`,
    method: 'post',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.16 提交作品 JSON（须 application/json，勿用 multipart；权限 SUBMIT_SUBMISSIONS）
// 字段：competition_id, team_id(null=个人), division(dual 必填), title, description?, file_id?, content_text?
// 请求体支持扁平对象或 { payload: { ... } }，此处使用扁平结构
export function submitCompetitionSubmission (payload) {
  const raw = payload || {}
  const competitionId = Number(raw.competition_id)
  if (!Number.isFinite(competitionId) || competitionId <= 0) {
    return Promise.reject(new Error('竞赛 ID 无效'))
  }
  const title = trimStr(raw.title)
  if (!title) {
    return Promise.reject(new Error('作品标题不能为空'))
  }
  const body = {
    competition_id: competitionId,
    title
  }
  const teamRaw = raw.team_id
  if (teamRaw != null && teamRaw !== '') {
    const teamId = Number(teamRaw)
    if (Number.isFinite(teamId) && teamId > 0) body.team_id = teamId
  } else if (Object.prototype.hasOwnProperty.call(raw, 'team_id')) {
    body.team_id = null
  }
  const division = trimStr(raw.division)
  if (division === 'undergraduate' || division === 'vocational') {
    body.division = division
  }
  const desc = trimStr(raw.description)
  if (desc) body.description = desc
  const contentText = raw.content_text
  if (contentText != null && String(contentText).trim() !== '') {
    body.content_text = String(contentText).trim()
  } else if (Object.prototype.hasOwnProperty.call(raw, 'content_text')) {
    body.content_text = null
  }
  if (raw.file_id != null && raw.file_id !== '') {
    const fileId = Number(raw.file_id)
    if (Number.isFinite(fileId) && fileId > 0) body.file_id = fileId
  }
  return axios({
    url: '/v1/competitions/submissions',
    method: 'post',
    data: body,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.16.1 提交作品 multipart（有文件时用；Form 含 competition_id / team_id / division / title 等）
export function uploadCompetitionSubmission (formData) {
  return axios({
    url: '/v1/competitions/submissions/upload',
    method: 'post',
    data: formData,
    timeout: 600000
  })
}

// 8.16.2 查看作品列表（dual 按提交时落库的 division 筛选）
export function getCompetitionSubmissions (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/submissions`,
    method: 'get',
    params: buildCompetitionDivisionParams(options)
  })
}

// 8.16.3 查看作品详情
export function getCompetitionSubmission (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}`,
    method: 'get'
  })
}

/** 从 Content-Disposition 解析下载文件名 */
function parseContentDispositionFilename (header) {
  const raw = header == null ? '' : String(header)
  if (!raw) return ''
  const star = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(raw)
  if (star && star[1]) {
    try {
      return decodeURIComponent(star[1].trim().replace(/^["']|["']$/g, ''))
    } catch (_) {
      return star[1].trim().replace(/^["']|["']$/g, '')
    }
  }
  const plain = /filename\s*=\s*([^;]+)/i.exec(raw)
  if (plain && plain[1]) {
    return plain[1].trim().replace(/^["']|["']$/g, '')
  }
  return ''
}

// 8.16.4 下载作品文件（保留响应头以还原原始文件名，避免落成 .bin）
export function downloadCompetitionSubmissionFile (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/download`,
    method: 'get',
    responseType: 'blob',
    timeout: 600000,
    __returnFullResponse: true
  }).then((res) => {
    const headers = (res && res.headers) || {}
    const cd = headers['content-disposition'] || headers['Content-Disposition'] || ''
    const filename =
      parseContentDispositionFilename(cd) || `submission_${submissionId}.zip`
    return { blob: res.data, filename }
  })
}

/** 超级管理员：按组别+赛道上传/覆盖竞赛试卷（竞赛须已 published/closed） */
export function uploadCompetitionExamPaper (competitionId, formData) {
  return axios({
    url: `/v1/competitions/${competitionId}/exam-papers`,
    method: 'post',
    data: formData,
    timeout: 600000
  })
}

/** 查询竞赛各组别/赛道试卷是否已发布 */
export function getCompetitionExamPapers (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/exam-papers`,
    method: 'get'
  })
}

/** 分题提交配置（题数/题名/分值区间） */
export function getSubmissionQuestionConfig (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/submission-question-config`,
    method: 'get'
  })
}

export function putSubmissionQuestionConfig (competitionId, payload) {
  return axios({
    url: `/v1/competitions/${competitionId}/submission-question-config`,
    method: 'put',
    data: payload,
    headers: { 'Content-Type': 'application/json' }
  })
}

/** 下载已发布试卷（已报名学生 / 关联指导老师；须传 division；建议传 work_track） */
export function downloadCompetitionExamPaper (competitionId, options = {}) {
  const params = {}
  if (options.division != null && options.division !== '') {
    params.division = options.division
  }
  if (options.work_track != null && options.work_track !== '') {
    params.work_track = options.work_track
  }
  return axios({
    url: `/v1/competitions/${competitionId}/exam-papers/download`,
    method: 'get',
    params,
    responseType: 'blob',
    timeout: 600000
  })
}

// 8.17 评分/审核（仅已核验且已指派 expert；权限 REVIEW_SUBMISSIONS）首次评分
export function reviewCompetitionSubmissionGrade (submissionId, payload) {
  // payload: { score: number, feedback?: string }
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'put',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.17.1 修改评分（已评分作品；PATCH）
export function patchCompetitionSubmissionReviewGrade (submissionId, payload) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'patch',
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.17.2 查询作品评分（ReviewResponse；与 PUT/PATCH 响应体一致，供教师端列表展示分数）
export function getCompetitionSubmissionReviewGrade (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/review-grade`,
    method: 'get'
  })
}

/** 查询某队五题评分 */
export function getTeamQuestionGrade (competitionId, teamId) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams/${teamId}/question-grades`,
    method: 'get'
  })
}

/** 首次按题评分 */
export function putTeamQuestionGrade (competitionId, teamId, payload) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams/${teamId}/question-grades`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 修改某队五题评分 */
export function patchTeamQuestionGrade (competitionId, teamId, payload) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams/${teamId}/question-grades`,
    method: 'patch',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.18 评分汇总（dual 须传 division，仅统计该组作品）
export function getCompetitionScoresSummary (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/scores/summary`,
    method: 'get',
    params: buildCompetitionDivisionParams(options)
  })
}

// 8.19 排行榜（dual 须传 division，组内排名）
export function getCompetitionRankings (competitionId, limit = 50, options = {}) {
  const params = buildCompetitionDivisionParams(options)
  if (limit != null && limit !== '') params.limit = limit
  return axios({
    url: `/v1/competitions/${competitionId}/scores/rankings`,
    method: 'get',
    params
  })
}

// 8.20 我的成绩（学生）
// GET /api/v1/competitions/{competition_id}/scores/me
// 响应：{ competition_id, submissions[] }；每条含作品字段 + score | null、feedback | null、reviewed_at | null（与 §8.17 评审计分一致）
export function getMyCompetitionScores (competitionId) {
  return axios({
    url: `/v1/competitions/${competitionId}/scores/me`,
    method: 'get'
  })
}

// 8.0.6 管理员：调整第二套帐号（role / expert_verified；仅 super_admin）
export function patchCompetitionAltUser (targetUserId, payload) {
  return axios({
    url: `/v1/competitions/admin/alt-users/${encodeURIComponent(targetUserId)}`,
    method: 'patch',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.0.7 管理员：全局专家列表（role=expert；含 assigned_competition_ids；super_admin）
export function getAllCompetitionExperts () {
  return axios({
    url: '/v1/competitions/experts',
    method: 'get'
  })
}

// 8.0.7 管理员：列出本赛专家（单赛；已指派 + 待审核 items）
export function getCompetitionExperts (competitionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts`,
    method: 'get'
  })
}

// 8.0.7 管理员：指派专家（目标须 expert 且 expert_verified=true；须传 team_ids）
export function assignCompetitionExpert (competitionId, expertUserId, payload = {}) {
  const body = payload && typeof payload === 'object' ? payload : {}
  const teamIds = Array.isArray(body.team_ids) ? body.team_ids : (Array.isArray(payload) ? payload : [])
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'post',
    data: { team_ids: teamIds },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.0.7 管理员：取消指派（可传 teamId 仅撤销单支队伍）
export function revokeCompetitionExpert (competitionId, expertUserId, options = {}) {
  const params = {}
  const teamId = options && options.teamId
  if (teamId != null && teamId !== '') {
    params.team_id = teamId
  }
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'delete',
    params
  })
}

// 8.11.5.1 校管理员：提交资料申请（multipart/form-data）
export function submitSchoolAdminApplication (formData) {
  return axios({
    url: '/v1/competitions/school-admin/application',
    method: 'post',
    data: formData
  })
}

// 8.11.5.1 校管理员：查看本人申请状态
export function getSchoolAdminApplicationMe () {
  return axios({
    url: '/v1/competitions/school-admin/application/me',
    method: 'get'
  })
}

// 8.11.5.1 校管理员：下载本人申请照片
export function getSchoolAdminApplicationPhoto () {
  return axios({
    url: '/v1/competitions/school-admin/application/photo',
    method: 'get',
    responseType: 'blob'
  })
}

// 8.11.5.2 超级管理员：校管申请列表
export function listSchoolAdminApplications (options = {}) {
  const params = {}
  const status = options && options.status
  if (status != null && String(status).trim() !== '' && String(status).trim().toLowerCase() !== 'all') {
    params.status = String(status).trim()
  } else if (status != null && String(status).trim().toLowerCase() === 'all') {
    params.status = 'all'
  }
  const keyword = options && (options.keyword != null ? options.keyword : options.school)
  if (keyword != null && String(keyword).trim() !== '') {
    params.keyword = String(keyword).trim()
  }
  return axios({
    url: '/v1/competitions/admin/school-admin-applications',
    method: 'get',
    params
  })
}

// 8.11.5.2 超级管理员：查看校管申请照片
export function getSchoolAdminApplicationPhotoAdmin (userId) {
  return axios({
    url: `/v1/competitions/admin/school-admin-applications/${encodeURIComponent(userId)}/photo`,
    method: 'get',
    responseType: 'blob'
  })
}

// 8.11.5.2 超级管理员：审核校管申请
export function reviewSchoolAdminApplication (userId, payload) {
  return axios({
    url: `/v1/competitions/admin/school-admin-applications/${encodeURIComponent(userId)}`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 8.11.5.3 校管理员：组队审核列表
export function getSchoolAdminTeams (options = {}) {
  const params = {}
  const status = options && options.status
  if (status != null && String(status).trim() !== '' && String(status).trim().toLowerCase() !== 'all') {
    params.status = String(status).trim()
  }
  const school = options && options.school
  if (school != null && String(school).trim() !== '') {
    params.school = String(school).trim()
  }
  const username = options && options.username
  if (username != null && String(username).trim() !== '') {
    params.username = String(username).trim()
  }
  const competitionId = options && options.competition_id
  const cid = Number(competitionId)
  if (Number.isFinite(cid) && cid > 0) {
    params.competition_id = cid
  }
  return axios({
    url: '/v1/competitions/school-admin/teams',
    method: 'get',
    params
  })
}

// 超级管理员：全部学校组队校审列表
export function listAdminTeamReviews (options = {}) {
  const params = {}
  const status = options && options.status
  if (status != null && String(status).trim() !== '') {
    params.status = String(status).trim()
  }
  const school = options && options.school
  if (school != null && String(school).trim() !== '') {
    params.school = String(school).trim()
  }
  const keyword = options && options.keyword
  if (keyword != null && String(keyword).trim() !== '') {
    params.keyword = String(keyword).trim()
  }
  const competitionId = options && options.competition_id
  const cid = Number(competitionId)
  if (Number.isFinite(cid) && cid > 0) {
    params.competition_id = cid
  }
  return axios({
    url: '/v1/competitions/admin/team-reviews',
    method: 'get',
    params
  })
}

// 8.11.5.3 校管理员：审核队伍
export function schoolReviewTeam (teamId, payload) {
  return axios({
    url: `/v1/competitions/teams/${encodeURIComponent(teamId)}/school-review`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 校管/超管：为队伍添加或更换指导老师 */
export function setTeamAdvisor (teamId, payload) {
  return axios({
    url: `/v1/competitions/teams/${encodeURIComponent(teamId)}/advisor`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 校管/超管：修改队伍组别与赛道 */
export function setTeamDivisionTrack (teamId, payload) {
  return axios({
    url: `/v1/competitions/teams/${encodeURIComponent(teamId)}/division-track`,
    method: 'put',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 校管代建队（直接已通过并报名） */
export function schoolAdminProxyCreateTeam (payload) {
  return axios({
    url: '/v1/competitions/school-admin/proxy-teams',
    method: 'post',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/** 校管补报名（队伍全员或个人） */
export function schoolAdminProxyEnroll (payload) {
  return axios({
    url: '/v1/competitions/school-admin/proxy-enroll',
    method: 'post',
    data: payload || {},
    headers: {
      'Content-Type': 'application/json'
    }
  })
}
