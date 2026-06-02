import { axios } from '@/utils/request'

/**
 * 竞赛报名系统接口封装（文档 §8：`GET|POST|PUT|DELETE /api/v1/competitions/...`）
 *
 * 鉴权：须由全局 axios 拦截器在请求头附带 **第二套 Alt JWT**（`POST /api/alt-identity/session` 签发），
 * 与主站 `access_token` **不可混用**。竞赛相关整型 ID（student_id / submitter_id / captain_id 等）
 * 语义均为 **alt_auth_users.id**，非主库 users.id。
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

// 8.1.1 获取竞赛详情（单条；含 division_mode / qr_layout / qr_codes，供详情页与组别弹窗判断）
export function getCompetition (competitionId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}`,
    method: 'get'
  })
}

/** 竞赛二维码图（GET，一般为 image/png）；dual 分开展示时可传 division */
export function getCompetitionQrCode (competitionId, options = {}) {
  const params = {}
  const div = options && options.division
  if (div === 'undergraduate' || div === 'vocational') {
    params.division = div
  }
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/qr-code`,
    method: 'get',
    params,
    responseType: 'blob'
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

// 8.11.1 导出队伍信息 Excel（dual 须传 division）
export function exportCompetitionTeamsExcel (competitionId, options = {}) {
  return axios({
    url: `/v1/competitions/${competitionId}/teams/export`,
    method: 'get',
    params: buildCompetitionDivisionParams(options),
    responseType: 'blob'
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

// 8.12 创建队伍（学生自建队长 / 指导老师组班；权限 MANAGE_TEAMS）
// 学生：{ competition_id, initial_member_ids?: null }
// 指导老师：{ competition_id, name?, captain_student_id?, initial_member_ids: number[] }（至少一名队员）
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

// 8.12.2 邀请队员（队长或建队指导老师）
export function inviteCompetitionTeamMember (teamId, studentId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/invite`,
    method: 'post',
    data: { student_id: studentId },
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

// 8.13 加入队伍（学生；权限 MANAGE_TEAMS）
export function addTeamMember (teamId) {
  return axios({
    url: `/v1/competitions/teams/${teamId}/members`,
    method: 'post'
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

// 8.16.4 下载作品文件
export function downloadCompetitionSubmissionFile (submissionId) {
  return axios({
    url: `/v1/competitions/submissions/${submissionId}/download`,
    method: 'get',
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

// 8.0.7 管理员：指派专家（目标须 expert 且 expert_verified=true）
export function assignCompetitionExpert (competitionId, expertUserId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'post'
  })
}

// 8.0.7 管理员：取消指派
export function revokeCompetitionExpert (competitionId, expertUserId) {
  return axios({
    url: `/v1/competitions/${encodeURIComponent(competitionId)}/experts/${encodeURIComponent(expertUserId)}`,
    method: 'delete'
  })
}
