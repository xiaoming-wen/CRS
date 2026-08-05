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
            <li>通过加载全部专家；待审核者点击 <strong>确定专家身份</strong>。</li>
            <li>已核验专家点击 <strong>指派</strong> → 选择竞赛并<strong>至少勾选一支队伍</strong> → 取消指派将撤销该竞赛下全部队伍。</li>
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
          <template slot="description">可在下方待审核列表中查找并核验。</template>
        </a-alert>

        <a-table
          row-key="expert_user_id"
          size="small"
          bordered
          :loading="registryLoading"
          :columns="pendingExpertsColumns"
          :data-source="pendingExpertsTableData"
          :pagination="pendingExpertsTableData.length > 8 ? { pageSize: 8 } : false"
          :locale="{ emptyText: '当前无待审核专家' }"
        >
          <template slot="pendingActions" slot-scope="text, record">
            <a-button
              type="primary"
              size="small"
              :loading="verifyLoadingId === record.expert_user_id"
              @click="handleVerifyExpertRow(record)"
            >
              确定专家身份
            </a-button>
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
                <div class="assignment-item__text">
                  <a-tag color="blue">{{ formatCompetitionLabel(a) }}</a-tag>
                  <span class="muted assignment-teams">
                    {{ formatAssignmentTeams(a) }}
                  </span>
                </div>
                <a-button
                  type="link"
                  size="small"
                  danger
                  :loading="revokeLoadingKey === `${a.competition_id}-${record.expert_user_id}`"
                  @click="handleRevokeAssignment(record, a)"
                >
                  取消指派
                </a-button>
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
      :width="640"
      @ok="submitAssignModal"
      @cancel="closeAssignModal"
    >
      <div v-if="assignModalExpert" class="assign-modal-body">
        <p class="assign-modal-expert">
          专家：<strong>{{ assignModalExpert.username }}</strong>
          <span class="muted">（ID {{ assignModalExpert.expert_user_id }}）</span>
        </p>
        <a-form-item label="选择竞赛" required :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
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
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="选择队伍" required :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
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
                v-for="t in assignModalTeamOptions"
                :key="t.id"
                :value="t.id"
                :disabled="t.alreadyAssigned"
              >
                {{ t.id }} — {{ t.name || '未命名队伍' }}
                <span v-if="t.alreadyAssigned" class="muted">（已指派）</span>
              </a-select-option>
            </a-select>
          </a-spin>
          <p v-if="assignModalCompetitionId && !assignModalTeamsLoading && !assignModalTeamOptions.length" class="muted" style="margin-top: 8px">
            该竞赛暂无队伍，请先完成组队后再指派。
          </p>
        </a-form-item>
        <p v-if="assignModalExpert.assignments && assignModalExpert.assignments.length" class="muted assign-modal-hint">
          已指派：{{ assignModalExpert.assignments.map(a => formatCompetitionLabel(a) + '（' + formatAssignmentTeams(a) + '）').join('；') }}
        </p>
      </div>
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
      verifyLoadingId: null,
      revokeLoadingKey: null,
      assignModalVisible: false,
      assignModalLoading: false,
      assignModalExpert: null,
      assignModalCompetitionId: undefined,
      assignModalTeamIds: [],
      assignModalTeamOptions: [],
      assignModalTeamsLoading: false,
      pendingExpertsColumns: [
        { title: '用户 ID', dataIndex: 'expert_user_id', key: 'expert_user_id', width: 88 },
        { title: '用户名', dataIndex: 'username', key: 'username', width: 140, ellipsis: true },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 140, ellipsis: true },
        { title: '操作', key: 'pendingActions', width: 140, scopedSlots: { customRender: 'pendingActions' } }
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
    routeExpertUserIdHint () {
      const q = this.$route && this.$route.query
      const raw = q && (q.expertUserId != null ? q.expertUserId : q.user_id)
      if (raw == null || String(raw).trim() === '') return null
      const n = Number(raw)
      return Number.isFinite(n) && n > 0 ? n : null
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
          return `${name}`
        })
        .join('、')
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
          team_name: t.team_name || null
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
        full_name: row.full_name != null && String(row.full_name).trim() !== '' ? String(row.full_name) : '—',
        school: row.school != null && String(row.school).trim() !== '' ? String(row.school) : '—',
        expert_verified: row.expert_verified === true,
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
        this.pendingExpertItems = all.filter(row => !row.expert_verified)
        this.verifiedExpertItems = all.filter(row => row.expert_verified)
      } catch (e) {
        this.pendingExpertItems = []
        this.verifiedExpertItems = []
        this.$message.error('加载专家列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.registryLoading = false
      }
    },
    async patchExpertVerified (targetId) {
      const res = await patchCompetitionAltUser(targetId, {
        role: 'expert',
        expert_verified: true
      })
      return this.normalizeVerifiedExpert(res, targetId)
    },
    async handleVerifyExpertRow (record) {
      if (!record || record.expert_user_id == null) return
      const targetId = Number(record.expert_user_id)
      this.verifyLoadingId = targetId
      try {
        await this.patchExpertVerified(targetId)
        this.$message.success(`用户 #${targetId} 专家身份已确认，可进行竞赛与队伍指派`)
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('核验失败：' + this.getApiErrorMessage(e))
      } finally {
        this.verifyLoadingId = null
      }
    },
    openAssignModal (record) {
      this.assignModalExpert = record
      this.assignModalCompetitionId = undefined
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      this.assignModalVisible = true
    },
    closeAssignModal () {
      this.assignModalVisible = false
      this.assignModalExpert = null
      this.assignModalCompetitionId = undefined
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      this.assignModalLoading = false
      this.assignModalTeamsLoading = false
    },
    async onAssignCompetitionChange (competitionId) {
      this.assignModalTeamIds = []
      this.assignModalTeamOptions = []
      const cid = Number(competitionId)
      if (!Number.isFinite(cid) || cid <= 0) return
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
              alreadyAssigned: already.has(id)
            }
          })
          .filter(Boolean)
          .sort((a, b) => a.id - b.id)
      } catch (e) {
        this.assignModalTeamOptions = []
        this.$message.error('加载队伍失败：' + this.getApiErrorMessage(e))
      } finally {
        this.assignModalTeamsLoading = false
      }
    },
    async submitAssignModal () {
      if (!this.assignModalExpert) return Promise.reject()
      const expertId = Number(this.assignModalExpert.expert_user_id)
      const competitionId = Number(this.assignModalCompetitionId)
      if (!Number.isFinite(competitionId) || competitionId <= 0) {
        this.$message.warning('请选择竞赛')
        return Promise.reject()
      }
      const teamIds = (this.assignModalTeamIds || [])
        .map(id => Number(id))
        .filter(n => Number.isFinite(n) && n > 0)
      if (!teamIds.length) {
        this.$message.warning('请至少选择一支队伍')
        return Promise.reject()
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
    },
    async handleRevokeAssignment (expertRecord, assignment) {
      if (!expertRecord || !assignment) return
      const expertId = Number(expertRecord.expert_user_id)
      const competitionId = Number(assignment.competition_id)
      const label = this.formatCompetitionLabel(assignment)
      try {
        await this.$confirm({
          title: '取消指派',
          content: `确定将专家 #${expertId} 从「${label}」及其全部指派队伍撤销吗？`,
          okText: '确定',
          cancelText: '取消',
          okType: 'danger'
        })
      } catch {
        return
      }
      this.revokeLoadingKey = `${competitionId}-${expertId}`
      try {
        await revokeCompetitionExpert(competitionId, expertId)
        this.$message.success('已取消指派')
        await this.loadExpertRegistry()
      } catch (e) {
        this.$message.error('取消失败：' + this.getApiErrorMessage(e))
      } finally {
        this.revokeLoadingKey = null
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

.assignment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assignment-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px;
}

.assignment-item__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.assignment-teams {
  font-size: 12px;
  line-height: 1.4;
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
