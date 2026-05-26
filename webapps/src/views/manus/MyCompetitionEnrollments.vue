<template>
  <div class="my-competition-enrollments">
    <a-card :bordered="false" class="section-card">
      <div class="toolbar">
        <a-button type="primary" :loading="loading" @click="fetchList">
          刷新
        </a-button>
      </div>
      <a-alert
        v-if="errorMsg"
        type="warning"
        show-icon
        :message="errorMsg"
        style="margin-top: 16px"
      />
      <div
        class="my-enrollments-table-scroll"
        :style="{ '--enrollment-table-min': enrollmentTableMinPx + 'px' }"
      >
        <a-table
          :columns="columns"
          :data-source="tableData"
          :loading="loading"
          :pagination="{ pageSize: 10, showSizeChanger: true }"
          row-key="key"
          size="middle"
          :locale="{ emptyText: '暂无报名记录' }"
        >
        <template slot="enrollStatus" slot-scope="text">
          <a-tag :color="enrollStatusColor(text)">{{ enrollStatusText(text) }}</a-tag>
        </template>
        <template slot="actions" slot-scope="text, record">
          <a-button
            type="primary"
            size="small"
            :loading="withdrawLoading"
            :disabled="withdrawLoading || !record || record.status !== 'enrolled'"
            @click="handleWithdraw(record)"
          >
            退赛
          </a-button>
        </template>
        <template slot="competitionStatus" slot-scope="text">
          <a-tag :color="competitionStatusColor(text)">{{ competitionStatusText(text) }}</a-tag>
        </template>
        </a-table>
      </div>
    </a-card>
  </div>
</template>

<script>
import { getMyCompetitionEnrollments, withdrawCompetition } from '@/api/competition'
import { markCompetitionWithdrawnForResubmit } from '@/utils/competitionSubmissionCycle'

/** 报名记录展示：仅使用接口返回值，空则显示 "-" */
function enrollmentCell (v) {
  if (v == null) return '-'
  const s = String(v).trim()
  return s === '' ? '-' : s
}

function schoolInfoFromEnrollment (row) {
  if (!row || typeof row !== 'object') return '-'
  const direct = row.school_info
  if (direct != null && String(direct).trim() !== '') return String(direct).trim()
  const school = row.school
  const college = row.college
  const a = school != null && String(school).trim() !== '' ? String(school).trim() : ''
  const b = college != null && String(college).trim() !== '' ? String(college).trim() : ''
  if (a && b) return `${a} · ${b}`
  return a || b || '-'
}

export default {
  name: 'MyCompetitionEnrollments',
  data () {
    return {
      loading: false,
      errorMsg: '',
      list: [],
      withdrawLoading: false,
      columns: [
        { title: '竞赛', dataIndex: 'competitionName', key: 'competitionName', ellipsis: true, width: 180 },
        { title: '竞赛状态', dataIndex: 'competitionStatus', key: 'competitionStatus', width: 82, scopedSlots: { customRender: 'competitionStatus' } },
        { title: '竞赛开始', dataIndex: 'start_at', key: 'start_at', width: 132 },
        { title: '竞赛结束', dataIndex: 'end_at', key: 'end_at', width: 132 },
        { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 96 },
        { title: '姓名', dataIndex: 'real_name', key: 'real_name', width: 80 },
        { title: '年级', dataIndex: 'grade', key: 'grade', width: 72 },
        { title: '联系方式', dataIndex: 'contact', key: 'contact', width: 118 },
        { title: '学校信息', dataIndex: 'school_info', key: 'school_info', ellipsis: true, width: 128 },
        { title: '队伍ID', dataIndex: 'team_id', key: 'team_id', width: 72 },
        {
          title: '队长',
          dataIndex: 'is_captain',
          key: 'is_captain',
          width: 56,
          customRender: (t) => (t === null || t === undefined ? '-' : (t ? '是' : '否'))
        },
        { title: '报名状态', dataIndex: 'status', key: 'status', width: 88, scopedSlots: { customRender: 'enrollStatus' } },
        { title: '报名时间', dataIndex: 'created_at', key: 'created_at', width: 148 },
        { title: '操作', key: 'actions', width: 92, scopedSlots: { customRender: 'actions' } }
      ]
    }
  },
  computed: {
    enrollmentTableMinPx () {
      return this.columns.reduce((sum, c) => sum + (typeof c.width === 'number' ? c.width : 0), 0)
    },
    tableData () {
      return this.list.map((row, index) => {
        const c = row.competition || {}

        // team_id === null 视为个人报名：不显示队伍相关信息
        const isTeam = row.team_id !== null && row.team_id !== undefined

        return {
          key: row.id != null ? `e-${row.id}` : `row-${index}`,
          id: row.id,
          competition_id: row.competition_id,
          competitionName: enrollmentCell(c.name || row.competition_name),
          competitionStatus: c.status,
          /** 以下字段仅来自报名接口返回，空显示 "-" */
          student_no: enrollmentCell(row.student_no),
          real_name: enrollmentCell(row.real_name),
          grade: enrollmentCell(row.grade),
          contact: enrollmentCell(row.contact),
          school_info: schoolInfoFromEnrollment(row),
          team_id: isTeam ? enrollmentCell(row.team_id) : '-',
          is_captain: isTeam ? !!row.is_captain : null,
          status: row.status,
          created_at: this.formatDateTime(row.created_at),
          start_at: this.formatDateTime(c.start_at),
          end_at: this.formatDateTime(c.end_at)
        }
      })
    }
  },
  mounted () {
    this.fetchList()
  },
  methods: {
    async handleWithdraw (record) {
      if (!record || record.competition_id == null) return
      if (record.status !== 'enrolled') return
      try {
        await this.$confirm({
          title: '确认退赛',
          content: '退赛后当前报名资格将取消；若再次报名，需重新提交作品。是否继续？',
          okText: '退赛',
          cancelText: '取消',
          okType: 'danger'
        })
      } catch {
        return
      }
      this.withdrawLoading = true
      try {
        await withdrawCompetition(record.competition_id)
        markCompetitionWithdrawnForResubmit(record.competition_id)
        this.$message.success('退赛成功，再次报名后请重新提交作品')
        await this.fetchList()
      } catch (e) {
        this.$message.error('退赛失败：' + (e && e.message ? e.message : '未知错误'))
      } finally {
        this.withdrawLoading = false
      }
    },

    formatDateTime (s) {
      if (!s) return '-'
      const d = new Date(s)
      if (Number.isNaN(d.getTime())) return s
      return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    },
    enrollStatusText (s) {
      const m = { enrolled: '已报名', cancelled: '已取消', withdrawn: '已退赛' }
      return m[s] || (s || '-')
    },
    enrollStatusColor (s) {
      const m = { enrolled: 'green', cancelled: 'default', withdrawn: 'red' }
      return m[s] || 'blue'
    },
    competitionStatusText (s) {
      const m = { draft: '草稿', published: '已发布', open: '报名中', closed: '已结束', upcoming: '即将开始' }
      return m[s] || (s || '-')
    },
    competitionStatusColor (s) {
      const m = { draft: 'default', published: 'green', open: 'green', closed: 'red', upcoming: 'blue' }
      return m[s] || 'default'
    },
    async fetchList () {
      this.loading = true
      this.errorMsg = ''
      try {
        const res = await getMyCompetitionEnrollments()
        if (Array.isArray(res)) this.list = res
        else if (res && Array.isArray(res.items)) this.list = res.items
        else if (res && Array.isArray(res.data)) this.list = res.data
        else this.list = []
      } catch (e) {
        this.list = []
        this.errorMsg = (e && e.message) ? String(e.message) : '加载失败'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.my-competition-enrollments {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.my-competition-enrollments .section-card {
  min-height: 400px;
  max-width: 100%;
}

.my-competition-enrollments ::v-deep .ant-card {
  max-width: 100%;
}

/* 整表（含分页）包在一层里横向滚动，滚动条在列表最下方 */
.my-enrollments-table-scroll {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  margin-top: 16px;
  overflow-x: auto;
  overflow-y: visible;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
  scrollbar-gutter: stable;
}

.my-enrollments-table-scroll ::v-deep .ant-table {
  min-width: var(--enrollment-table-min, 1486px);
}

.my-enrollments-table-scroll ::v-deep .ant-table table {
  min-width: var(--enrollment-table-min, 1486px);
}

.my-enrollments-table-scroll ::v-deep .ant-table-body {
  overflow-x: visible !important;
}

.my-enrollments-table-scroll::-webkit-scrollbar {
  height: 10px;
}

.my-enrollments-table-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.28);
  border-radius: 5px;
}

.my-enrollments-table-scroll::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.06);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
