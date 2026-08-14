<template>
  <div class="competition-school-admin-team-review">
    <a-card :bordered="false" class="section-card">
      <a-spin :spinning="applicationLoading">
        <a-alert
          v-if="isSchoolMode && !canReviewTeams"
          type="warning"
          show-icon
          message="暂不可校审"
          description="请先在「申请校管」提交资料并经超级管理员审核通过后，方可审核本校组队。"
          style="margin-bottom: 16px"
        />

        <template v-else>
          <a-alert type="info" show-icon :message="alertTitle" style="margin-bottom: 16px">
            <template slot="description">
              <div>{{ alertDescription }}</div>
              <div v-if="isSchoolMode" style="margin-top: 6px">
                校管「代建队报名」创建后队伍直接为「已通过」；学生/老师自建仍进入待校审。
              </div>
            </template>
          </a-alert>

          <div class="page-toolbar">
            <a-select
              v-model="teamStatusFilter"
              style="width: 180px; margin-right: 8px"
              @change="loadTeams"
            >
              <a-select-option value="all">所有</a-select-option>
              <a-select-option value="pending_school_review">待校审</a-select-option>
              <a-select-option value="active">已通过</a-select-option>
              <a-select-option value="rejected">已驳回</a-select-option>
            </a-select>
            <a-input-search
              v-model="schoolKeyword"
              allow-clear
              placeholder="搜索学校"
              style="width: 220px; margin-right: 8px"
              @search="loadTeams"
              @pressEnter="loadTeams"
            />
            <a-button :loading="teamsLoading" @click="loadTeams">刷新</a-button>
            <a-button
              v-if="isSchoolMode"
              type="primary"
              style="margin-left: 8px"
              @click="openProxyTeamModal"
            >
              代建队报名
            </a-button>
          </div>

          <a-table
            row-key="team_id"
            size="small"
            bordered
            :loading="teamsLoading"
            :columns="teamColumns"
            :data-source="teamItems"
            :pagination="teamItems.length > 10 ? { pageSize: 10, showSizeChanger: true } : false"
            :scroll="{ x: 1200 }"
            :locale="{ emptyText: '暂无队伍数据' }"
          >
            <template slot="advisorName" slot-scope="text">
              {{ text && String(text).trim() ? String(text).trim() : '—' }}
            </template>
            <template slot="competitionStartAt" slot-scope="text">
              {{ formatDateTime(text) }}
            </template>
            <template slot="competitionEndAt" slot-scope="text">
              {{ formatDateTime(text) }}
            </template>
            <template slot="members" slot-scope="text, record">
              <span v-if="!record.members || !record.members.length" class="muted">—</span>
              <span v-else>
                {{ record.members.map(m => formatMemberLabel(m)).join('、') }}
              </span>
            </template>
            <template slot="teamStatus" slot-scope="text">
              <a-tag :color="teamStatusColor(text)">{{ teamStatusText(text) }}</a-tag>
            </template>
            <template slot="teamActions" slot-scope="text, record">
              <div class="team-actions-cell">
                <template v-if="record.status === 'pending_school_review'">
                  <a-button
                    type="primary"
                    size="small"
                    :loading="reviewLoadingId === record.team_id && reviewAction === 'approve'"
                    @click="handleReviewTeam(record, 'approve')"
                  >
                    通过
                  </a-button>
                  <a-button
                    size="small"
                    danger
                    :loading="reviewLoadingId === record.team_id && reviewAction === 'reject'"
                    @click="openRejectModal(record)"
                  >
                    驳回
                  </a-button>
                </template>
                <a-button
                  v-if="record.status !== 'rejected'"
                  size="small"
                  @click="openAdvisorModal(record)"
                >
                  添加/修改指导老师
                </a-button>
                <span v-if="record.status === 'rejected'" class="muted">—</span>
              </div>
            </template>
          </a-table>
        </template>
      </a-spin>
    </a-card>

    <a-modal
      :visible="rejectModalVisible"
      title="驳回队伍"
      :confirm-loading="rejectModalLoading"
      ok-text="确认驳回"
      ok-type="danger"
      cancel-text="取消"
      destroy-on-close
      @ok="submitRejectModal"
      @cancel="closeRejectModal"
    >
      <p v-if="rejectModalTeam">
        确定驳回队伍「{{ rejectModalTeam.team_name || ('#' + rejectModalTeam.team_id) }}」吗？
      </p>
      <a-form-item label="驳回原因" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
        <a-textarea v-model="rejectFeedback" :rows="3" placeholder="选填" />
      </a-form-item>
    </a-modal>

    <a-modal
      :visible="advisorModalVisible"
      title="添加/修改指导老师"
      :confirm-loading="advisorModalLoading"
      ok-text="保存"
      cancel-text="取消"
      destroy-on-close
      @ok="submitAdvisorModal"
      @cancel="closeAdvisorModal"
    >
      <p v-if="advisorModalTeam" style="margin-bottom: 8px">
        队伍「{{ advisorModalTeam.team_name || ('#' + advisorModalTeam.team_id) }}」
      </p>
      <p class="muted" style="margin-bottom: 12px">
        当前指导老师：
        <span v-if="advisorModalCurrentAdvisorLabel">{{ advisorModalCurrentAdvisorLabel }}</span>
        <span v-else>未设置</span>
      </p>
      <a-form :label-col="{ span: 7 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="指导老师" required>
          <a-input
            v-model="advisorForm.advisor_ref"
            placeholder="姓名、用户名或 8 位用户 ID"
            allow-clear
          />
        </a-form-item>
      </a-form>
      <p class="muted" style="margin: 0; font-size: 12px">
        未设置时可添加；已有老师时填写新信息即可修改替换。
      </p>
    </a-modal>

    <a-modal
      :visible="proxyTeamVisible"
      title="代建队报名"
      :confirm-loading="proxyTeamLoading"
      ok-text="创建并报名"
      cancel-text="取消"
      destroy-on-close
      width="640px"
      @ok="submitProxyTeam"
      @cancel="closeProxyTeamModal"
    >
      <a-form :label-col="{ span: 6 }" :wrapper-col="{ span: 17 }">
        <a-form-item label="竞赛" required>
          <a-select
            v-model="proxyTeamForm.competition_id"
            show-search
            option-filter-prop="children"
            placeholder="选择竞赛"
            :loading="competitionsLoading"
            style="width: 100%"
          >
            <a-select-option
              v-for="c in teamCompetitions"
              :key="c.id"
              :value="c.id"
            >
              {{ c.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="队名">
          <a-input v-model="proxyTeamForm.team_name" placeholder="选填" />
        </a-form-item>
        <a-form-item label="组别" required>
          <a-radio-group v-model="proxyTeamForm.division">
            <a-radio-button value="undergraduate">本科</a-radio-button>
            <a-radio-button value="vocational">高职</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="赛道" required>
          <a-radio-group v-model="proxyTeamForm.work_track">
            <a-radio-button value="works">作品</a-radio-button>
            <a-radio-button value="software">软件</a-radio-button>
            <a-radio-button value="hardware">硬件</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="队长用户名" required>
          <a-input v-model="proxyTeamForm.captain_username" placeholder="学生用户名" />
        </a-form-item>
        <a-form-item label="队员用户名" required>
          <a-textarea
            v-model="proxyTeamForm.member_usernames_text"
            :rows="3"
            placeholder="多名用逗号或换行分隔；可含队长"
          />
        </a-form-item>
        <a-form-item label="指导老师用户名">
          <a-input v-model="proxyTeamForm.advisor_username" placeholder="选填" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import {
  getSchoolAdminApplicationMe,
  getSchoolAdminTeams,
  listAdminTeamReviews,
  schoolReviewTeam,
  setTeamAdvisor,
  schoolAdminProxyCreateTeam,
  getCompetitions
} from '@/api/competition'

const TEAM_STATUS_MAP = {
  pending_school_review: { text: '待校审', color: 'orange' },
  active: { text: '已通过', color: 'green' },
  rejected: { text: '已驳回', color: 'red' }
}

function emptyProxyTeamForm () {
  return {
    competition_id: undefined,
    team_name: '',
    division: 'undergraduate',
    work_track: 'works',
    captain_username: '',
    member_usernames_text: '',
    advisor_username: ''
  }
}

export default {
  name: 'CompetitionSchoolAdminTeamReview',
  props: {
    mode: {
      type: String,
      default: 'school',
      validator: v => v === 'school' || v === 'super'
    }
  },
  data () {
    return {
      applicationLoading: false,
      canReviewTeams: false,
      teamsLoading: false,
      teamStatusFilter: 'all',
      schoolKeyword: '',
      teamItems: [],
      reviewLoadingId: null,
      reviewAction: null,
      rejectModalVisible: false,
      rejectModalLoading: false,
      rejectModalTeam: null,
      rejectFeedback: '',
      advisorModalVisible: false,
      advisorModalLoading: false,
      advisorModalTeam: null,
      advisorForm: {
        advisor_ref: ''
      },
      competitionsLoading: false,
      competitions: [],
      proxyTeamVisible: false,
      proxyTeamLoading: false,
      proxyTeamForm: emptyProxyTeamForm()
    }
  },
  computed: {
    isSchoolMode () {
      return this.mode !== 'super'
    },
    alertTitle () {
      return this.isSchoolMode ? '组队校审' : '队伍校审'
    },
    alertDescription () {
      if (this.isSchoolMode) {
        return '审核本校学生/指导老师创建的组队申请。通过后队伍状态为「已通过」，方可组队参赛；驳回后相关报名自动退赛。校管与超管共享同一审核状态。'
      }
      return '查看各校组队申请并执行通过/驳回。与校管共享同一队伍状态：任一方审核后双方列表同步更新。'
    },
    teamCompetitions () {
      return (this.competitions || []).filter(c => c && c.allow_team !== false)
    },
    advisorModalCurrentAdvisorLabel () {
      const t = this.advisorModalTeam
      if (!t) return ''
      const name = t.advisor_name != null ? String(t.advisor_name).trim() : ''
      if (name) {
        return t.advisor_id != null ? `${name}（ID ${t.advisor_id}）` : name
      }
      return t.advisor_id != null ? `ID ${t.advisor_id}` : ''
    },
    teamColumns () {
      return [
        { title: '竞赛', dataIndex: 'competition_name', key: 'competition_name', width: 160, ellipsis: true },
        { title: '开始时间', dataIndex: 'competition_start_at', key: 'competition_start_at', width: 150, scopedSlots: { customRender: 'competitionStartAt' } },
        { title: '结束时间', dataIndex: 'competition_end_at', key: 'competition_end_at', width: 150, scopedSlots: { customRender: 'competitionEndAt' } },
        { title: '学校', dataIndex: 'school', key: 'school', width: 120, ellipsis: true },
        { title: '指导老师', dataIndex: 'advisor_name', key: 'advisor_name', width: 100, ellipsis: true, scopedSlots: { customRender: 'advisorName' } },
        { title: '队伍名', dataIndex: 'team_name', key: 'team_name', width: 120, ellipsis: true },
        { title: '队长', dataIndex: 'captain_name', key: 'captain_name', width: 100, ellipsis: true },
        { title: '队员', key: 'members', scopedSlots: { customRender: 'members' }, width: 200, ellipsis: true },
        { title: '状态', dataIndex: 'status', key: 'status', width: 90, scopedSlots: { customRender: 'teamStatus' } },
        { title: '操作', key: 'teamActions', width: 260, fixed: 'right', scopedSlots: { customRender: 'teamActions' } }
      ]
    }
  },
  mounted () {
    void this.bootstrap()
  },
  methods: {
    async bootstrap () {
      if (this.isSchoolMode) {
        await this.checkReviewPermission()
        if (this.canReviewTeams) {
          await this.loadTeams()
        }
      } else {
        this.canReviewTeams = true
        await this.loadTeams()
      }
    },
    getApiErrorMessage (error, fallback = '操作失败') {
      const respData = error && error.response ? error.response.data : null
      const raw =
        (respData && (respData.detail || respData.message || respData.error)) ||
        (error && error.message) ||
        ''
      if (Array.isArray(raw)) {
        return raw.map(item => (item && item.msg) ? item.msg : String(item)).join('；')
      }
      return typeof raw === 'string' ? raw : (raw ? JSON.stringify(raw) : fallback)
    },
    formatDateTime (value) {
      if (!value) return '—'
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return String(value)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
    },
    formatMemberLabel (m) {
      if (!m) return '—'
      const name = m.full_name || m.username || `#${m.user_id}`
      return m.is_captain ? `${name}（队长）` : name
    },
    teamStatusText (status) {
      return (TEAM_STATUS_MAP[status] || { text: status || '—' }).text
    },
    teamStatusColor (status) {
      return (TEAM_STATUS_MAP[status] || { color: 'default' }).color
    },
    parseUsernameList (text) {
      return String(text || '')
        .split(/[\s,，;；]+/)
        .map(s => s.trim())
        .filter(Boolean)
    },
    async checkReviewPermission () {
      this.applicationLoading = true
      try {
        const res = await getSchoolAdminApplicationMe()
        this.canReviewTeams = res && res.can_review_teams === true
      } catch (e) {
        this.canReviewTeams = false
        this.$message.error('加载校审权限失败：' + this.getApiErrorMessage(e))
      } finally {
        this.applicationLoading = false
      }
    },
    parseTeamsList (res) {
      if (!res) return []
      const items = Array.isArray(res) ? res : (Array.isArray(res.items) ? res.items : [])
      return items.filter(Boolean)
    },
    async loadTeams () {
      this.teamsLoading = true
      try {
        const params = {
          status: this.teamStatusFilter,
          school: (this.schoolKeyword || '').trim() || undefined
        }
        const res = this.isSchoolMode
          ? await getSchoolAdminTeams(params)
          : await listAdminTeamReviews({
            ...params,
            keyword: params.school
          })
        this.teamItems = this.parseTeamsList(res)
      } catch (e) {
        this.teamItems = []
        this.$message.error('加载组队列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.teamsLoading = false
      }
    },
    async ensureCompetitionsLoaded () {
      if (this.competitions.length) return
      this.competitionsLoading = true
      try {
        const res = await getCompetitions()
        this.competitions = Array.isArray(res) ? res : (Array.isArray(res && res.items) ? res.items : [])
      } catch (e) {
        this.competitions = []
        this.$message.error('加载竞赛列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.competitionsLoading = false
      }
    },
    async handleReviewTeam (record, action, feedback) {
      if (!record || record.team_id == null) return
      const teamId = Number(record.team_id)
      this.reviewLoadingId = teamId
      this.reviewAction = action
      try {
        await schoolReviewTeam(teamId, {
          action,
          feedback: feedback != null ? feedback : undefined
        })
        this.$message.success(action === 'approve' ? '已通过审核' : '已驳回')
        await this.loadTeams()
      } catch (e) {
        this.$message.error('审核失败：' + this.getApiErrorMessage(e))
        throw e
      } finally {
        this.reviewLoadingId = null
        this.reviewAction = null
      }
    },
    openRejectModal (record) {
      this.rejectModalTeam = record
      this.rejectFeedback = ''
      this.rejectModalVisible = true
    },
    closeRejectModal () {
      this.rejectModalVisible = false
      this.rejectModalTeam = null
      this.rejectFeedback = ''
      this.rejectModalLoading = false
    },
    async submitRejectModal () {
      if (!this.rejectModalTeam) return Promise.reject(new Error('cancelled'))
      this.rejectModalLoading = true
      try {
        await this.handleReviewTeam(
          this.rejectModalTeam,
          'reject',
          (this.rejectFeedback || '').trim() || undefined
        )
        this.closeRejectModal()
      } catch (e) {
        return Promise.reject(e)
      } finally {
        this.rejectModalLoading = false
      }
    },
    openAdvisorModal (record) {
      this.advisorModalTeam = record
      this.advisorForm = { advisor_ref: '' }
      this.advisorModalVisible = true
    },
    closeAdvisorModal () {
      this.advisorModalVisible = false
      this.advisorModalTeam = null
      this.advisorForm = { advisor_ref: '' }
      this.advisorModalLoading = false
    },
    async submitAdvisorModal () {
      if (!this.advisorModalTeam || this.advisorModalTeam.team_id == null) {
        return Promise.reject(new Error('cancelled'))
      }
      const ref = String(this.advisorForm.advisor_ref || '').trim()
      if (!ref) {
        this.$message.warning('请填写指导老师姓名、用户名或用户 ID')
        return Promise.reject(new Error('cancelled'))
      }
      const payload = /^\d{8}$/.test(ref)
        ? { advisor_id: Number(ref) }
        : { advisor_name: ref }
      this.advisorModalLoading = true
      try {
        await setTeamAdvisor(this.advisorModalTeam.team_id, payload)
        this.$message.success(this.advisorModalCurrentAdvisorLabel ? '指导老师已修改' : '指导老师已添加')
        this.closeAdvisorModal()
        await this.loadTeams()
      } catch (e) {
        this.$message.error('设置失败：' + this.getApiErrorMessage(e))
        return Promise.reject(e)
      } finally {
        this.advisorModalLoading = false
      }
    },
    async openProxyTeamModal () {
      this.proxyTeamForm = emptyProxyTeamForm()
      this.proxyTeamVisible = true
      await this.ensureCompetitionsLoaded()
    },
    closeProxyTeamModal () {
      this.proxyTeamVisible = false
      this.proxyTeamLoading = false
      this.proxyTeamForm = emptyProxyTeamForm()
    },
    async submitProxyTeam () {
      const form = this.proxyTeamForm
      const competitionId = Number(form.competition_id)
      const captainUsername = String(form.captain_username || '').trim()
      let memberUsernames = this.parseUsernameList(form.member_usernames_text)
      if (!Number.isFinite(competitionId) || competitionId <= 0) {
        this.$message.warning('请选择竞赛')
        return Promise.reject(new Error('cancelled'))
      }
      if (!captainUsername) {
        this.$message.warning('请填写队长用户名')
        return Promise.reject(new Error('cancelled'))
      }
      if (!memberUsernames.length) {
        memberUsernames = [captainUsername]
      } else {
        const hasCaptain = memberUsernames.some(
          u => String(u).trim().toLowerCase() === captainUsername.toLowerCase()
        )
        if (!hasCaptain) {
          memberUsernames = [captainUsername, ...memberUsernames]
        }
      }
      const payload = {
        competition_id: competitionId,
        team_name: (form.team_name || '').trim() || undefined,
        captain_username: captainUsername,
        member_usernames: memberUsernames,
        division: form.division,
        work_track: form.work_track
      }
      const advisorUsername = String(form.advisor_username || '').trim()
      if (advisorUsername) {
        payload.advisor_username = advisorUsername
      }
      this.proxyTeamLoading = true
      try {
        await schoolAdminProxyCreateTeam(payload)
        this.$message.success('代建队成功，队伍已通过并完成报名')
        this.closeProxyTeamModal()
        this.teamStatusFilter = 'active'
        await this.loadTeams()
      } catch (e) {
        this.$message.error('代建队失败：' + this.getApiErrorMessage(e))
        return Promise.reject(e)
      } finally {
        this.proxyTeamLoading = false
      }
    }
  }
}
</script>

<style scoped lang="less">
.competition-school-admin-team-review {
  width: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.page-toolbar {
  margin-bottom: 12px;
}

.team-actions-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.muted {
  color: rgba(0, 0, 0, 0.45);
}
</style>
