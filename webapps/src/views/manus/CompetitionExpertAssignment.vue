<template>
  <div class="competition-expert-assignment">
    <a-card :bordered="false" class="section-card">
      <a-steps :current="workflowStep" size="small" style="margin-bottom: 24px">
        <a-step title="核验专家" />
        <a-step title="指派竞赛与队伍" />
      </a-steps>

      <a-alert type="info" show-icon message="专家注册与指派流程" style="margin-bottom: 16px">
        <template slot="description">
          <ol class="expert-assignment-desc-list">
            <li>用户可在注册页选择 <strong>专家</strong> 自助注册，此时，<strong>无法登录</strong>。</li>
            <li>通过加载全部专家；可按<strong>姓名</strong>与<strong>状态</strong>筛选，对<strong>待核验</strong>执行通过或未通过。</li>
            <li>已核验专家点击 <strong>指派</strong> → 选择竞赛，按<strong>组别</strong>与<strong>赛道</strong>筛选并勾选队伍（可全选当前筛选）→ 可对某一支队伍点击 <strong>取消指派</strong>。</li>
          </ol>
        </template>
      </a-alert>

      <div class="page-toolbar">
        <a-button :loading="registryLoading" @click="loadExpertRegistry">
          刷新全部
        </a-button>
      </div>

      <a-card size="small" title="手动核验专家" :bordered="true" class="sub-block">
        <a-alert
          v-if="routeExpertUserIdHint != null"
          type="info"
          show-icon
          style="margin-bottom: 12px"
          :message="`注册专家用户 ID：${routeExpertUserIdHint}`"
        >
          <template slot="description">可在下方列表中按姓名/状态查找并核验。</template>
        </a-alert>

        <div class="expert-verify-filters" style="margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center">
          <a-input-search
            v-model="expertNameKeyword"
            allow-clear
            placeholder="按姓名 / 用户名搜索"
            style="width: 240px"
            @search="() => {}"
          />
          <a-select
            v-model="expertStatusFilter"
            style="width: 140px"
            placeholder="状态"
          >
            <a-select-option value="all">全部状态</a-select-option>
            <a-select-option value="pending">待核验</a-select-option>
            <a-select-option value="approved">已通过</a-select-option>
            <a-select-option value="rejected">未通过</a-select-option>
          </a-select>
          <span class="muted">共 {{ allExpertsFilteredTableData.length }} 人</span>
        </div>

        <a-table
          row-key="expert_user_id"
          size="small"
          bordered
          :loading="registryLoading"
          :columns="allExpertsColumns"
          :data-source="allExpertsFilteredTableData"
          :pagination="{ pageSize: 10, showSizeChanger: true }"
          :scroll="{ x: 1100 }"
          :locale="{ emptyText: '暂无专家账号' }"
        >
          <template slot="phone" slot-scope="text">
            {{ text || '—' }}
          </template>
          <template slot="school" slot-scope="text">
            {{ text || '—' }}
          </template>
          <template slot="expertStatus" slot-scope="text, record">
            <div class="expert-status-cell">
              <a-tag :color="expertStatusMeta(record).color">{{ expertStatusMeta(record).text }}</a-tag>
              <div
                v-if="expertReviewStatus(record) === 'rejected' && record.expert_review_feedback"
                class="expert-reject-reason"
                :title="record.expert_review_feedback"
              >
                原因：{{ record.expert_review_feedback }}
              </div>
            </div>
          </template>
          <template slot="allExpertActions" slot-scope="text, record">
            <template v-if="expertReviewStatus(record) === 'pending'">
              <a-button
                type="primary"
                size="small"
                :loading="verifyLoadingId === record.expert_user_id && verifyAction === 'approve'"
                @click="handleVerifyExpertRow(record)"
              >
                确定专家身份
              </a-button>
              <a-button
                type="danger"
                size="small"
                style="margin-left: 8px"
                :loading="verifyLoadingId === record.expert_user_id && verifyAction === 'reject'"
                @click="openRejectExpertModal(record)"
              >
                未通过
              </a-button>
            </template>
            <template v-else-if="expertReviewStatus(record) === 'rejected'">
              <a-button
                size="small"
                :loading="verifyLoadingId === record.expert_user_id && verifyAction === 'restore'"
                @click="handleRestorePendingExpert(record)"
              >
                恢复待审
              </a-button>
            </template>
            <span v-else class="muted">已通过，可在下方指派</span>
          </template>
        </a-table>
      </a-card>

      <a-card
        size="small"
        title="竞赛指派专家列表"
        :bordered="true"
        class="sub-block"
        style="margin-top: 16px"
      >
        <a-table
          row-key="expert_user_id"
          size="small"
          bordered
          :loading="registryLoading"
          :columns="verifiedExpertsColumns"
          :data-source="verifiedExpertsTableData"
          :pagination="{ pageSize: 10, showSizeChanger: true }"
          :scroll="{ x: 1080 }"
          :locale="{ emptyText: '暂无已核验专家，请先在上方完成核验' }"
        >
          <template slot="assignments" slot-scope="text, record">
            <span v-if="!record.assignments || !record.assignments.length" class="muted">尚未指派</span>
            <div v-else class="assignment-list">
              <div
                v-for="a in record.assignments"
                :key="`${record.expert_user_id}-${a.competition_id}`"
                class="assignment-item"
              >
                <div class="assignment-item__comp">
                  <a-tag color="blue">{{ formatCompetitionLabel(a) }}</a-tag>
                </div>
                <div v-if="!(a.teams && a.teams.length)" class="muted assignment-teams">
                  未指定队伍（不可评阅）
                </div>
                <div
                  v-for="t in (a.teams || [])"
                  :key="`${record.expert_user_id}-${a.competition_id}-${t.team_id}`"
                  class="assignment-team-row"
                >
                  <span class="assignment-team-name">
                    {{ t.team_name || ('队伍#' + t.team_id) }}
                    <span class="muted">（ID {{ t.team_id }}{{ formatTeamDivisionTrackSuffix(t) }}）</span>
                  </span>
                  <a-button
                    type="link"
                    size="small"
                    danger
                    :loading="revokeLoadingKey === revokeKeyOf(record.expert_user_id, a.competition_id, t.team_id)"
                    @click="openRevokeModal(record, a, t)"
                  >
                    取消指派
                  </a-button>
                </div>
              </div>
            </div>
          </template>
          <template slot="verifiedActions" slot-scope="text, record">
            <a-button type="primary" size="small" @click="openAssignModal(record)">
              指派
            </a-button>
          </template>
        </a-table>
      </a-card>
    </a-card>

    <a-modal
      :visible="assignModalVisible"
      title="指派专家到竞赛队伍"
      :confirm-loading="assignModalLoading"
      ok-text="确认指派"
      cancel-text="取消"
      destroy-on-close
      :width="720"
      @ok="submitAssignModal"
      @cancel="closeAssignModal"
    >
      <div v-if="assignModalExpert" class="assign-modal-body">
        <p class="assign-modal-expert">
          专家：<strong>{{ assignModalExpert.username }}</strong>
          <span class="muted">（ID {{ assignModalExpert.expert_user_id }}）</span>
        </p>
        <a-alert
          type="info"
          show-icon
          style="margin-bottom: 12px"
          message="请先选择竞赛，再按本科/高职组别与赛道筛选队伍；可一键全选当前组别×赛道下尚未指派的队伍。"
        />
        <a-form-item label="选择竞赛" required :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <a-select
            v-model="assignModalCompetitionId"
            show-search
            option-filter-prop="children"
            placeholder="请选择要指派的竞赛"
            style="width: 100%"
            @change="onAssignCompetitionChange"
          >
            <a-select-option
              v-for="c in competitions"
              :key="c.id"
              :value="c.id"
            >
              {{ c.id }} — {{ c.name || '未命名' }}（{{ getStatusText(c.status) }}）
              <span v-if="isCompetitionDual(c)" class="muted"> · 双组别</span>
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="组别" required :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <a-radio-group
            v-model="assignModalDivisionFilter"
            :disabled="!assignModalCompetitionId"
            button-style="solid"
          >
            <a-radio-button value="undergraduate">本科</a-radio-button>
            <a-radio-button value="vocational">高职</a-radio-button>
            <a-radio-button value="all">全部组别</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="赛道" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <a-radio-group
            v-model="assignModalTrackFilter"
            :disabled="!assignModalCompetitionId"
            button-style="solid"
          >
            <a-radio-button value="all">全部赛道</a-radio-button>
            <a-radio-button value="works">作品</a-radio-button>
            <a-radio-button value="software">软件</a-radio-button>
            <a-radio-button value="hardware">硬件</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="选择队伍" required :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
          <div style="margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 8px">
            <a-button
              size="small"
              :disabled="!assignModalFilteredSelectableIds.length"
              @click="selectAllFilteredTeams"
            >
              全选当前筛选（{{ assignModalFilteredSelectableIds.length }}）
            </a-button>
            <a-button
              size="small"
              :disabled="!(assignModalTeamIds && assignModalTeamIds.length)"
              @click="assignModalTeamIds = []"
            >
              清空已选
            </a-button>
            <span class="muted" style="line-height: 24px">
              已选 {{ (assignModalTeamIds || []).length }} 支
              · 筛选可见 {{ assignModalFilteredTeamOptions.length }} 支
            </span>
          </div>
          <a-spin :spinning="assignModalTeamsLoading">
            <a-select
              v-model="assignModalTeamIds"
              mode="multiple"
              show-search
              option-filter-prop="children"
              placeholder="请至少选择一支队伍"
              style="width: 100%"
              :disabled="!assignModalCompetitionId"
            >
              <a-select-option
                v-for="t in assignModalFilteredTeamOptions"
                :key="t.id"
                :value="t.id"
                :disabled="t.alreadyAssigned"
              >
                {{ formatTeamOptionLabel(t) }}
                <span v-if="t.alreadyAssigned" class="muted">（已指派）</span>
              </a-select-option>
            </a-select>
          </a-spin>
          <p v-if="assignModalCompetitionId && !assignModalTeamsLoading && !assignModalTeamOptions.length" class="muted" style="margin-top: 8px">
            该竞赛暂无队伍，请先完成组队后再指派。
          </p>
          <p
            v-else-if="assignModalCompetitionId && !assignModalTeamsLoading && assignModalTeamOptions.length && !assignModalFilteredTeamOptions.length"
            class="muted"
            style="margin-top: 8px"
          >
            当前组别/赛道筛选下暂无队伍，请调整筛选条件。
          </p>
        </a-form-item>
        <p v-if="assignModalExpert.assignments && assignModalExpert.assignments.length" class="muted assign-modal-hint">
          已指派：{{ assignModalExpert.assignments.map(a => formatCompetitionLabel(a) + '（' + formatAssignmentTeams(a) + '）').join('；') }}
        </p>
      </div>
    </a-modal>

    <a-modal
      :visible="revokeModalVisible"
      title="取消指派"
      :confirm-loading="revokeModalLoading"
      ok-text="确认取消"
      ok-type="danger"
      cancel-text="返回"
      destroy-on-close
      @ok="submitRevokeModal"
      @cancel="closeRevokeModal"
    >
      <p v-if="revokeModalPayload">
        确定取消专家
        <strong>#{{ revokeModalPayload.expertId }}</strong>
        （{{ revokeModalPayload.expertName }}）
        对竞赛「{{ revokeModalPayload.competitionLabel }}」中队伍
        <strong>{{ revokeModalPayload.teamLabel }}</strong>
        的指派吗？
      </p>
      <p class="muted" style="margin: 8px 0 0">仅取消该队伍，不影响同竞赛下其他已指派队伍。</p>
    </a-modal>
    <a-modal
      :visible="rejectExpertModalVisible"
      title="专家核验未通过"
      :confirm-loading="rejectExpertModalLoading"
      ok-text="确认未通过"
      ok-type="danger"
      cancel-text="返回"
      destroy-on-close
      @ok="submitRejectExpertModal"
      @cancel="closeRejectExpertModal"
    >
      <p v-if="rejectExpertModalRecord">
        确定将专家
        <strong>#{{ rejectExpertModalRecord.expert_user_id }}</strong>
        （{{ rejectExpertModalRecord.username }}）
        标记为<strong>未通过</strong>吗？该用户登录时将看到下方原因，并需重新注册。
      </p>
      <a-form-item label="未通过原因" required style="margin-top: 12px; margin-bottom: 0">
        <a-textarea
          v-model="rejectExpertFeedback"
          :rows="3"
          :max-length="500"
          placeholder="请填写未通过原因（用户登录时可见）"
        />
      </a-form-item>
    </a-modal>
  </div>
</template>

<script>
import {
  getCompetitions,
  getCompetitionTeams,
  getAllCompetitionExperts,
  patchCompetitionAltUser,
  assignCompetitionExpert,
  revokeCompetitionExpert
} from '@/api/competition'
import { normalizeCompetitionApiList } from '@/utils/competitionSubmissionCycle'

export default {
  name: 'CompetitionExpertAssignment',
  data () {
    return {
      workflowStep: 0,
      competitions: [],
      competitionsLoading: false,
      registryLoading: false,
      pendingExpertItems: [],
      verifiedExpertItems: [],
      rejectedExpertItems: [],
      allExpertItems: [],
      expertNameKeyword: '',
      expertStatusFilter: 'all',
      verifyLoadingId: null,
      verifyAction: null,
      rejectExpertModalVisible: false,
      rejectExpertModalLoading: false,
      rejectExpertModalRecord: null,
      rejectExpertFeedback: '',
      revokeLoadingKey: null,
      revokeModalVisible: false,
      revokeModalLoading: false,
      revokeModalPayload: null,
      assignModalVisible: false,
      assignModalLoading: false,
      assignModalExpert: null,
      assignModalCompetitionId: undefined,
      assignModalTeamIds: [],
      assignModalTeamOptions: [],
      assignModalTeamsLoading: false,
      assignModalDivisionFilter: 'undergraduate',
      assignModalTrackFilter: 'all',
      assignModalCompetitionIsDual: false,
      allExpertsColumns: [
        { title: '用户 ID', dataIndex: 'expert_user_id', key: 'expert_user_id', width: 88 },
        { title: '用户名', dataIndex: 'username', key: 'username', width: 120, ellipsis: true },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 100, ellipsis: true },
        { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120, scopedSlots: { customRender: 'phone' } },
        { title: '学校', dataIndex: 'school', key: 'school', width: 160, ellipsis: true, scopedSlots: { customRender: 'school' } },
        { title: '状态', key: 'expertStatus', width: 96, scopedSlots: { customRender: 'expertStatus' } },
        { title: '操作', key: 'allExpertActions', width: 240, fixed: 'right', scopedSlots: { customRender: 'allExpertActions' } }
      ],
      verifiedExpertsColumns: [
        { title: '用户 ID', dataIndex: 'expert_user_id', key: 'expert_user_id', width: 88 },
        { title: '用户名', dataIndex: 'username', key: 'username', width: 120, ellipsis: true },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 120, ellipsis: true },
        { title: '已指派竞赛与队伍', key: 'assignments', scopedSlots: { customRender: 'assignments' } },
        { title: '操作', key: 'verifiedActions', width: 88, fixed: 'right', scopedSlots: { customRender: 'verifiedActions' } }
      ]
    }
  },
  computed: {
    pendingExpertsTableData () {
      return (this.pendingExpertItems || []).map(row => ({
        ...row,
        key: `pending-${row.expert_user_id}`
      }))
    },
    verifiedExpertsTableData () {
      return (this.verifiedExpertItems || []).map(row => ({
        ...row,
        key: `verified-${row.expert_user_id}`
      }))
    },
    allExpertsFilteredTableData () {
      const kw = String(this.expertNameKeyword || '').trim().toLowerCase()
      const status = this.expertStatusFilter || 'all'
      return (this.allExpertItems || [])
        .filter((row) => {
          if (!row) return false
          const st = this.expertReviewStatus(row)
          if (status !== 'all' && st !== status) return false
          if (!kw) return true
          const name = String(row.full_name || '').toLowerCase()
          const username = String(row.username || '').toLowerCase()
          return name.includes(kw) || username.includes(kw)
        })
        .map(row => ({
          ...row,
          key: `all-${row.expert_user_id}`
        }))
    },
    routeExpertUserIdHint () {
      const q = this.$route && this.$route.query
      const raw = q && (q.expertUserId != null ? q.expertUserId : q.user_id)
      if (raw == null || String(raw).trim() === '') return null
      const n = Number(raw)
      return Number.isFinite(n) && n > 0 ? n : null
    },
    assignModalDivisionOptions () {
      return [
        { value: 'undergraduate', label: '本科' },
        { value: 'vocational', label: '高职' }
      ]
    },
    assignModalFilteredTeamOptions () {
      const list = this.assignModalTeamOptions || []
      const div = this.assignModalDivisionFilter
      const track = this.assignModalTrackFilter
      return list.filter((t) => {
        if (!t) return false
        if (div && div !== 'all') {
          const td = this.normalizeDivision(t.division)
          // 组别仅按本科 / 高职匹配（报名与建队均使用这两类）
          if (td !== div) return false
        }
        if (track && track !== 'all') {
          const tt = this.normalizeTrack(t.work_track)
          if (tt !== track) return false
        }
        return true
      })
    },
    assignModalFilteredSelectableIds () {
      return (this.assignModalFilteredTeamOptions || [])
        .filter(t => t && !t.alreadyAssigned)
        .map(t => t.id)
    }
  },
  watch: {
    verifiedExpertItems: {
      handler (list) {
        this.workflowStep = (list && list.length) ? 1 : 0
      },
      deep: true
    }
  },
  mounted () {
    void this.bootstrap()
  },
  methods: {
    async bootstrap () {
      await this.fetchCompetitions()
      await this.loadExpertRegistry()
    },
    getStatusText (status) {
      const map = { draft: '草稿', published: '已发布', open: '报名中', closed: '已结束' }
      return map[status] || (status || '未知')
    },
    formatCompetitionLabel (assignment) {
      if (!assignment) return '—'
      const name = assignment.competition_name || '未命名'
      return `${assignment.competition_id} — ${name}`
    },
    formatAssignmentTeams (assignment) {
      const teams = assignment && Array.isArray(assignment.teams) ? assignment.teams : []
      if (!teams.length) return '未指定队伍（不可评阅）'
      return teams
        .map(t => {
          const name = t.team_name || `队伍#${t.team_id}`
          const suffix = this.formatTeamDivisionTrackSuffix(t)
          return suffix ? `${name}${suffix}` : name
        })
        .join('、')
    },
    normalizeDivision (raw) {
      const s = raw != null ? String(raw).trim().toLowerCase() : ''
      if (s === 'undergraduate' || s === '本科' || s === '本科组') return 'undergraduate'
      if (s === 'vocational' || s === '高职' || s === '高职组') return 'vocational'
      return s || ''
    },
    normalizeTrack (raw) {
      const s = raw != null ? String(raw).trim().toLowerCase() : ''
      if (s === 'works' || s === 'software' || s === 'hardware') return s
      return ''
    },
    divisionLabel (raw) {
      const d = this.normalizeDivision(raw)
      if (d === 'undergraduate') return '本科'
      if (d === 'vocational') return '高职'
      return ''
    },
    trackLabel (raw) {
      const t = this.normalizeTrack(raw)
      if (t === 'works') return '作品赛道'
      if (t === 'software') return '软件赛道'
      if (t === 'hardware') return '硬件赛道'
      return ''
    },
    formatTeamDivisionTrackSuffix (t) {
      if (!t) return ''
      const parts = []
      const d = this.divisionLabel(t.division)
      const tr = this.trackLabel(t.work_track)
      if (d) parts.push(d)
      if (tr) parts.push(tr)
      return parts.length ? ` · ${parts.join(' · ')}` : ''
    },
    formatTeamOptionLabel (t) {
      if (!t) return ''
      const base = `${t.id} — ${t.name || '未命名队伍'}`
      const suffix = this.formatTeamDivisionTrackSuffix(t)
      return suffix ? `${base}${suffix}` : base
    },
    isCompetitionDual (comp) {
      if (!comp || typeof comp !== 'object') return false
      const mode = comp.division_mode != null ? comp.division_mode : comp.divisionMode
      return String(mode || '').toLowerCase() === 'dual'
    },
    revokeKeyOf (expertId, competitionId, teamId) {
      return `${competitionId}-${expertId}-${teamId}`
    },
    openRevokeModal (expertRecord, assignment, team) {
      if (!expertRecord || !assignment || !team) return
      const expertId = Number(expertRecord.expert_user_id)
      const competitionId = Number(assignment.competition_id)
      const teamId = Number(team.team_id)
      if (!Number.isFinite(expertId) || !Number.isFinite(competitionId) || !Number.isFinite(teamId)) {
        return
      }
      this.revokeModalPayload = {
        expertId,
        expertName: expertRecord.username || expertRecord.full_name || '—',
        competitionId,
        competitionLabel: this.formatCompetitionLabel(assignment),
        teamId,
        teamLabel: `${team.team_name || ('队伍#' + teamId)}（ID ${teamId}）`
      }
      this.revokeModalVisible = true
    },
    closeRevokeModal () {
      this.revokeModalVisible = false
      this.revokeModalLoading = false
      this.revokeModalPayload = null
    },
    async submitRevokeModal () {
      const payload = this.revokeModalPayload
      if (!payload) return Promise.reject(new Error('cancelled'))
      const { expertId, competitionId, teamId } = payload
      this.revokeModalLoading = true
      this.revokeLoadingKey = this.revokeKeyOf(expertId, competitionId, teamId)
      try {
        await revokeCompetitionExpert(competitionId, expertId, { teamId })
        this.$message.success('已取消该队伍指派')
        this.closeRevokeModal()
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('取消失败：' + this.getApiErrorMessage(e))
        return Promise.reject(e)
      } finally {
        this.revokeModalLoading = false
        this.revokeLoadingKey = null
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
    normalizeVerifiedExpert (res, fallbackId) {
      if (!res || typeof res !== 'object') {
        return {
          id: fallbackId,
          username: undefined,
          full_name: undefined,
          role: 'expert',
          expert_verified: true
        }
      }
      return {
        id: res.id != null ? res.id : fallbackId,
        username: res.username,
        full_name: res.full_name,
        role: res.role != null ? res.role : 'expert',
        expert_verified: res.expert_verified === true
      }
    },
    getCompetitionNameById (competitionId) {
      const cid = Number(competitionId)
      const found = (this.competitions || []).find(c => Number(c.id) === cid)
      return found ? (found.name || '未命名') : `竞赛 #${cid}`
    },
    buildAssignmentsFromExpertRow (row) {
      const assignedIds = Array.isArray(row.assigned_competition_ids)
        ? row.assigned_competition_ids
        : []
      const teamRows = Array.isArray(row.assigned_teams) ? row.assigned_teams : []
      const teamsByComp = {}
      teamRows.forEach((t) => {
        if (!t || t.competition_id == null || t.team_id == null) return
        const cid = Number(t.competition_id)
        if (!Number.isFinite(cid)) return
        if (!teamsByComp[cid]) teamsByComp[cid] = []
        teamsByComp[cid].push({
          team_id: Number(t.team_id),
          team_name: t.team_name || null,
          division: t.division != null ? String(t.division) : null,
          work_track: t.work_track != null ? String(t.work_track) : null
        })
      })
      const compIds = new Set([
        ...assignedIds.map(id => Number(id)).filter(n => Number.isFinite(n)),
        ...Object.keys(teamsByComp).map(k => Number(k))
      ])
      return Array.from(compIds)
        .sort((a, b) => a - b)
        .map(cid => ({
          competition_id: cid,
          competition_name: this.getCompetitionNameById(cid),
          teams: teamsByComp[cid] || []
        }))
    },
    parseGlobalExpertsList (res) {
      if (res == null) return []
      let items = []
      if (Array.isArray(res)) {
        items = res
      } else if (typeof res === 'object') {
        if (Array.isArray(res.items)) items = res.items
        else if (Array.isArray(res.data)) items = res.data
      }
      return items
        .map(row => this.parseGlobalExpertItem(row))
        .filter(Boolean)
    },
    parseGlobalExpertItem (row) {
      if (!row || typeof row !== 'object') return null
      const rawId = row.expert_user_id != null ? row.expert_user_id : row.user_id
      const expertUserId = Number(rawId)
      if (!Number.isFinite(expertUserId)) return null
      const assignedIds = Array.isArray(row.assigned_competition_ids)
        ? row.assigned_competition_ids
        : (Array.isArray(row.assignedCompetitionIds) ? row.assignedCompetitionIds : [])
      return {
        expert_user_id: expertUserId,
        username: row.username != null ? String(row.username) : '—',
        email: row.email != null ? String(row.email) : '',
        phone: row.phone != null && String(row.phone).trim() !== '' ? String(row.phone) : '',
        full_name: row.full_name != null && String(row.full_name).trim() !== '' ? String(row.full_name) : '—',
        school: row.school != null && String(row.school).trim() !== '' ? String(row.school) : '—',
        expert_verified: row.expert_verified === true,
        is_active: row.is_active !== false,
        expert_review_feedback:
          row.expert_review_feedback != null && String(row.expert_review_feedback).trim() !== ''
            ? String(row.expert_review_feedback).trim()
            : '',
        assigned_competition_ids: assignedIds.map(id => Number(id)).filter(n => Number.isFinite(n)),
        assigned_teams: Array.isArray(row.assigned_teams) ? row.assigned_teams : [],
        assignments: this.buildAssignmentsFromExpertRow(row)
      }
    },
    async fetchCompetitions () {
      this.competitionsLoading = true
      try {
        const res = await getCompetitions()
        const list = normalizeCompetitionApiList(res)
        this.competitions = list.map(item => {
          if (!item || typeof item !== 'object') return item
          const rid = item.id != null ? item.id : item.competition_id
          return rid != null ? { ...item, id: rid } : item
        })
      } catch (e) {
        this.competitions = []
        this.$message.error('获取竞赛列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.competitionsLoading = false
      }
    },
    async loadExpertRegistry () {
      this.registryLoading = true
      try {
        const res = await getAllCompetitionExperts()
        const all = this.parseGlobalExpertsList(res)
        this.allExpertItems = all
        // 待审：未核验且仍启用；已通过：已核验；未通过：停用且未核验
        this.pendingExpertItems = all.filter(row => !row.expert_verified && row.is_active !== false)
        this.verifiedExpertItems = all.filter(row => row.expert_verified)
        this.rejectedExpertItems = all.filter(row => !row.expert_verified && row.is_active === false)
      } catch (e) {
        this.allExpertItems = []
        this.pendingExpertItems = []
        this.verifiedExpertItems = []
        this.rejectedExpertItems = []
        this.$message.error('加载专家列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.registryLoading = false
      }
    },
    expertReviewStatus (record) {
      if (!record) return 'pending'
      if (record.expert_verified) return 'approved'
      if (record.is_active === false) return 'rejected'
      return 'pending'
    },
    expertStatusMeta (record) {
      const st = this.expertReviewStatus(record)
      if (st === 'approved') return { text: '已通过', color: 'green' }
      if (st === 'rejected') return { text: '未通过', color: 'red' }
      return { text: '待核验', color: 'orange' }
    },
    async patchExpertVerified (targetId) {
      const res =         await patchCompetitionAltUser(targetId, {
          role: 'expert',
          expert_verified: true,
          is_active: true,
          expert_review_feedback: ''
        })
      return this.normalizeVerifiedExpert(res, targetId)
    },
    async handleVerifyExpertRow (record) {
      if (!record || record.expert_user_id == null) return
      const targetId = Number(record.expert_user_id)
      this.verifyLoadingId = targetId
      this.verifyAction = 'approve'
      try {
        await this.patchExpertVerified(targetId)
        this.$message.success(`用户 #${targetId} 专家身份已确认，可进行竞赛与队伍指派`)
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('核验失败：' + this.getApiErrorMessage(e))
      } finally {
        this.verifyLoadingId = null
        this.verifyAction = null
      }
    },
    openRejectExpertModal (record) {
      if (!record || record.expert_user_id == null) return
      this.rejectExpertModalRecord = record
      this.rejectExpertFeedback = ''
      this.rejectExpertModalVisible = true
    },
    closeRejectExpertModal () {
      this.rejectExpertModalVisible = false
      this.rejectExpertModalLoading = false
      this.rejectExpertModalRecord = null
      this.rejectExpertFeedback = ''
    },
    async submitRejectExpertModal () {
      const record = this.rejectExpertModalRecord
      if (!record || record.expert_user_id == null) return Promise.reject(new Error('cancelled'))
      const reason = String(this.rejectExpertFeedback || '').trim()
      if (!reason) {
        this.$message.warning('请填写未通过原因')
        return Promise.reject(new Error('cancelled'))
      }
      const targetId = Number(record.expert_user_id)
      this.rejectExpertModalLoading = true
      this.verifyLoadingId = targetId
      this.verifyAction = 'reject'
      try {
        await patchCompetitionAltUser(targetId, {
          role: 'expert',
          expert_verified: false,
          is_active: false,
          expert_review_feedback: reason
        })
        this.$message.success(`用户 #${targetId} 已标记为未通过`)
        this.closeRejectExpertModal()
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('操作失败：' + this.getApiErrorMessage(e))
        return Promise.reject(e)
      } finally {
        this.rejectExpertModalLoading = false
        this.verifyLoadingId = null
        this.verifyAction = null
      }
    },
    async handleRestorePendingExpert (record) {
      if (!record || record.expert_user_id == null) return
      const targetId = Number(record.expert_user_id)
      this.verifyLoadingId = targetId
      this.verifyAction = 'restore'
      try {
        await patchCompetitionAltUser(targetId, {
          role: 'expert',
          expert_verified: false,
          is_active: true,
          expert_review_feedback: ''
        })
        this.$message.success(`用户 #${targetId} 已恢复为待核验`)
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('恢复失败：' + this.getApiErrorMessage(e))
      } finally {
        this.verifyLoadingId = null
        this.verifyAction = null
      }
    },
    openAssignModal (record) {
      this.assignModalExpert = record
      this.assignModalCompetitionId = undefined
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      this.assignModalDivisionFilter = 'undergraduate'
      this.assignModalTrackFilter = 'all'
      this.assignModalCompetitionIsDual = false
      this.assignModalVisible = true
    },
    closeAssignModal () {
      this.assignModalVisible = false
      this.assignModalExpert = null
      this.assignModalCompetitionId = undefined
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      this.assignModalDivisionFilter = 'undergraduate'
      this.assignModalTrackFilter = 'all'
      this.assignModalCompetitionIsDual = false
      this.assignModalLoading = false
      this.assignModalTeamsLoading = false
    },
    selectAllFilteredTeams () {
      const ids = this.assignModalFilteredSelectableIds || []
      const current = new Set((this.assignModalTeamIds || []).map(id => Number(id)))
      ids.forEach((id) => current.add(Number(id)))
      this.assignModalTeamIds = Array.from(current)
    },
    async onAssignCompetitionChange (competitionId) {
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      this.assignModalDivisionFilter = 'undergraduate'
      this.assignModalTrackFilter = 'all'
      const cid = Number(competitionId)
      if (!Number.isFinite(cid) || cid <= 0) {
        this.assignModalCompetitionIsDual = false
        return
      }
      const comp = (this.competitions || []).find(c => Number(c.id) === cid)
      this.assignModalCompetitionIsDual = this.isCompetitionDual(comp)
      this.assignModalTeamsLoading = true
      try {
        const res = await getCompetitionTeams(cid)
        const list = normalizeCompetitionApiList(res)
        const already = new Set(
          ((this.assignModalExpert && this.assignModalExpert.assigned_teams) || [])
            .filter(t => Number(t.competition_id) === cid)
            .map(t => Number(t.team_id))
            .filter(n => Number.isFinite(n))
        )
        this.assignModalTeamOptions = list
          .map((t) => {
            if (!t || typeof t !== 'object') return null
            const id = Number(t.id != null ? t.id : t.team_id)
            if (!Number.isFinite(id)) return null
            return {
              id,
              name: t.name || t.team_name || `队伍#${id}`,
              division: t.division != null ? String(t.division) : '',
              work_track: t.work_track != null ? String(t.work_track) : '',
              alreadyAssigned: already.has(id)
            }
          })
          .filter(Boolean)
          .sort((a, b) => {
            const order = { undergraduate: 0, vocational: 1 }
            const da = this.normalizeDivision(a.division)
            const db = this.normalizeDivision(b.division)
            const oa = order[da] != null ? order[da] : 9
            const ob = order[db] != null ? order[db] : 9
            if (oa !== ob) return oa - ob
            const ta = this.normalizeTrack(a.work_track) || 'zzz'
            const tb = this.normalizeTrack(b.work_track) || 'zzz'
            if (ta !== tb) return ta.localeCompare(tb)
            return a.id - b.id
          })
      } catch (e) {
        this.assignModalTeamOptions = []
        this.$message.error('加载队伍失败：' + this.getApiErrorMessage(e))
      } finally {
        this.assignModalTeamsLoading = false
      }
    },
    async submitAssignModal () {
      if (!this.assignModalExpert) return Promise.reject(new Error('cancelled'))
      const expertId = Number(this.assignModalExpert.expert_user_id)
      const competitionId = Number(this.assignModalCompetitionId)
      if (!Number.isFinite(competitionId) || competitionId <= 0) {
        this.$message.warning('请选择竞赛')
        return Promise.reject(new Error('cancelled'))
      }
      const teamIds = (this.assignModalTeamIds || [])
        .map(id => Number(id))
        .filter(n => Number.isFinite(n) && n > 0)
      if (!teamIds.length) {
        this.$message.warning('请至少选择一支队伍')
        return Promise.reject(new Error('cancelled'))
      }
      this.assignModalLoading = true
      try {
        await assignCompetitionExpert(competitionId, expertId, { team_ids: teamIds })
        this.$message.success('指派成功')
        this.closeAssignModal()
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('指派失败：' + this.getApiErrorMessage(e))
        return Promise.reject(e)
      } finally {
        this.assignModalLoading = false
      }
    }
  }
}
</script>

<style scoped lang="less">
.competition-expert-assignment {
  width: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.sub-block {
  background: #fafafa;
}

.page-toolbar {
  margin-bottom: 12px;
}

.expert-assignment-desc-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.6;
}

.muted {
  color: rgba(0, 0, 0, 0.45);
}

.expert-status-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.expert-reject-reason {
  max-width: 220px;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(0, 0, 0, 0.45);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.assignment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.assignment-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.assignment-item__comp {
  margin-bottom: 2px;
}

.assignment-team-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px;
  padding-left: 4px;
}

.assignment-team-name {
  font-size: 13px;
  line-height: 1.4;
}

.assignment-teams {
  font-size: 12px;
  line-height: 1.4;
  padding-left: 4px;
}

.assign-modal-body {
  padding-top: 4px;
}

.assign-modal-expert {
  margin-bottom: 16px;
}

.assign-modal-hint {
  margin-top: 8px;
  font-size: 12px;
}
</style>
