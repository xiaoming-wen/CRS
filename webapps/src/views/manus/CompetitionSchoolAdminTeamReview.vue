<template>
  <div class="competition-school-admin-team-review">
    <a-card :bordered="false" class="section-card">
      <a-spin :spinning="applicationLoading">
        <a-alert
          v-if="!canReviewTeams"
          type="warning"
          show-icon
          message="暂不可校审"
          description="请先在「申请校管」提交资料并经超级管理员审核通过后，方可审核本校组队。"
          style="margin-bottom: 16px"
        />

        <template v-else>
          <a-alert type="info" show-icon message="组队校审" style="margin-bottom: 16px">
            <template slot="description">
              审核本校学生/指导老师创建的组队申请。通过后队伍状态为「已通过」，方可组队参赛；驳回后相关报名自动退赛。
            </template>
          </a-alert>

          <div class="page-toolbar">
            <a-select
              v-model="teamStatusFilter"
              style="width: 180px; margin-right: 8px"
              @change="loadTeams"
            >
              <a-select-option value="pending_school_review">待校审</a-select-option>
              <a-select-option value="active">已通过</a-select-option>
              <a-select-option value="rejected">已驳回</a-select-option>
            </a-select>
            <a-button :loading="teamsLoading" @click="loadTeams">刷新</a-button>
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
                  style="margin-left: 8px"
                  :loading="reviewLoadingId === record.team_id && reviewAction === 'reject'"
                  @click="openRejectModal(record)"
                >
                  驳回
                </a-button>
              </template>
              <span v-else class="muted">—</span>
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
  </div>
</template>

<script>
import {
  getSchoolAdminApplicationMe,
  getSchoolAdminTeams,
  schoolReviewTeam
} from '@/api/competition'

const TEAM_STATUS_MAP = {
  pending_school_review: { text: '待校审', color: 'orange' },
  active: { text: '已通过', color: 'green' },
  rejected: { text: '已驳回', color: 'red' }
}

export default {
  name: 'CompetitionSchoolAdminTeamReview',
  data () {
    return {
      applicationLoading: false,
      canReviewTeams: false,
      teamsLoading: false,
      teamStatusFilter: 'pending_school_review',
      teamItems: [],
      reviewLoadingId: null,
      reviewAction: null,
      rejectModalVisible: false,
      rejectModalLoading: false,
      rejectModalTeam: null,
      rejectFeedback: ''
    }
  },
  computed: {
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
        { title: '操作', key: 'teamActions', width: 140, fixed: 'right', scopedSlots: { customRender: 'teamActions' } }
      ]
    }
  },
  mounted () {
    void this.bootstrap()
  },
  methods: {
    async bootstrap () {
      await this.checkReviewPermission()
      if (this.canReviewTeams) {
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
        const res = await getSchoolAdminTeams({ status: this.teamStatusFilter })
        this.teamItems = this.parseTeamsList(res)
      } catch (e) {
        this.teamItems = []
        this.$message.error('加载组队列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.teamsLoading = false
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
      if (!this.rejectModalTeam) return Promise.reject()
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

.muted {
  color: rgba(0, 0, 0, 0.45);
}
</style>
