<template>
  <div class="competition-school-admin-applications">
    <a-card :bordered="false" class="section-card">
      <a-alert type="info" show-icon message="校管理员资料审核" style="margin-bottom: 16px">
        <template slot="description">
          校管理员注册后可登录，但须提交资料（含照片）并经超级管理员审核通过后，方可执行本校组队校审。
        </template>
      </a-alert>

      <div class="page-toolbar">
        <a-select
          v-model="statusFilter"
          style="width: 160px; margin-right: 8px"
          @change="loadApplications"
        >
          <a-select-option value="all">所有</a-select-option>
          <a-select-option value="pending">待审核</a-select-option>
          <a-select-option value="approved">已通过</a-select-option>
          <a-select-option value="rejected">已驳回</a-select-option>
          <a-select-option value="not_submitted">未提交</a-select-option>
        </a-select>
        <a-input-search
          v-model="searchKeyword"
          allow-clear
          placeholder="用户ID / 用户名 / 姓名 / 学校"
          style="width: 280px; margin-right: 8px"
          @search="onSearch"
        />
        <a-button :loading="listLoading" @click="loadApplications">刷新</a-button>
      </div>

      <a-table
        row-key="user_id"
        size="small"
        bordered
        :loading="listLoading"
        :columns="columns"
        :data-source="tableData"
        :pagination="tableData.length > 10 ? { pageSize: 10, showSizeChanger: true } : false"
        :scroll="{ x: 1100 }"
        :locale="{ emptyText: '暂无申请记录' }"
      >
        <template slot="submittedAt" slot-scope="text">
          {{ formatDateTime(text) }}
        </template>
        <template slot="appStatus" slot-scope="text">
          <a-tag :color="statusColor(text)">{{ statusText(text) }}</a-tag>
        </template>
        <template slot="actions" slot-scope="text, record">
          <a-button
            v-if="record.photo_url"
            type="link"
            size="small"
            @click="openPhotoModal(record)"
          >
            查看照片
          </a-button>
          <template v-if="record.application_status === 'pending'">
            <a-button
              type="primary"
              size="small"
              :loading="reviewLoadingId === record.user_id && reviewAction === 'approve'"
              @click="handleReview(record, 'approve')"
            >
              通过
            </a-button>
            <a-button
              size="small"
              danger
              style="margin-left: 8px"
              :loading="reviewLoadingId === record.user_id && reviewAction === 'reject'"
              @click="openRejectModal(record)"
            >
              驳回
            </a-button>
          </template>
          <span v-else-if="!record.photo_url" class="muted">—</span>
        </template>
      </a-table>
    </a-card>

    <a-modal
      :visible="photoModalVisible"
      title="校管申请照片"
      :footer="null"
      width="480px"
      destroy-on-close
      @cancel="closePhotoModal"
    >
      <a-spin :spinning="photoModalLoading">
        <img v-if="photoModalUrl" :src="photoModalUrl" alt="申请照片" class="photo-modal-img" />
        <a-empty v-else description="暂无照片" />
      </a-spin>
    </a-modal>

    <a-modal
      :visible="rejectModalVisible"
      title="驳回校管申请"
      :confirm-loading="rejectModalLoading"
      ok-text="确认驳回"
      ok-type="danger"
      cancel-text="取消"
      destroy-on-close
      @ok="submitRejectModal"
      @cancel="closeRejectModal"
    >
      <p v-if="rejectModalRecord">
        确定驳回用户 #{{ rejectModalRecord.user_id }}（{{ rejectModalRecord.username }}）的校管申请吗？
      </p>
      <a-form-item label="审核备注" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
        <a-textarea v-model="rejectFeedback" :rows="3" placeholder="选填" />
      </a-form-item>
    </a-modal>
  </div>
</template>

<script>
import {
  listSchoolAdminApplications,
  getSchoolAdminApplicationPhotoAdmin,
  reviewSchoolAdminApplication
} from '@/api/competition'

const STATUS_MAP = {
  not_submitted: { text: '未提交', color: 'default' },
  pending: { text: '待审核', color: 'orange' },
  approved: { text: '已通过', color: 'green' },
  rejected: { text: '已驳回', color: 'red' }
}

export default {
  name: 'CompetitionSchoolAdminApplications',
  data () {
    return {
      statusFilter: 'all',
      searchKeyword: '',
      listLoading: false,
      applicationItems: [],
      reviewLoadingId: null,
      reviewAction: null,
      photoModalVisible: false,
      photoModalLoading: false,
      photoModalUrl: null,
      photoModalUserId: null,
      rejectModalVisible: false,
      rejectModalLoading: false,
      rejectModalRecord: null,
      rejectFeedback: ''
    }
  },
  computed: {
    columns () {
      return [
        { title: '用户 ID', dataIndex: 'user_id', key: 'user_id', width: 88 },
        { title: '用户名', dataIndex: 'username', key: 'username', width: 120, ellipsis: true },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 100, ellipsis: true },
        { title: '学校', dataIndex: 'school', key: 'school', width: 140, ellipsis: true },
        { title: '联系方式', dataIndex: 'application_contact', key: 'application_contact', width: 120, ellipsis: true },
        { title: '申请备注', dataIndex: 'application_remark', key: 'application_remark', width: 140, ellipsis: true },
        { title: '提交时间', dataIndex: 'application_submitted_at', key: 'application_submitted_at', width: 150, scopedSlots: { customRender: 'submittedAt' } },
        { title: '状态', dataIndex: 'application_status', key: 'application_status', width: 90, scopedSlots: { customRender: 'appStatus' } },
        { title: '操作', key: 'actions', width: 200, fixed: 'right', scopedSlots: { customRender: 'actions' } }
      ]
    },
    tableData () {
      const kw = (this.searchKeyword || '').trim().toLowerCase()
      const rows = (this.applicationItems || []).map(row => ({
        ...row,
        key: `app-${row.user_id}`
      }))
      if (!kw) return rows
      return rows.filter((row) => this.rowMatchesKeyword(row, kw))
    }
  },
  mounted () {
    void this.loadApplications()
  },
  beforeDestroy () {
    this.revokePhotoModalUrl()
  },
  methods: {
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
    statusText (status) {
      return (STATUS_MAP[status] || { text: status || '—' }).text
    },
    statusColor (status) {
      return (STATUS_MAP[status] || { color: 'default' }).color
    },
    onSearch (value) {
      if (value !== undefined && value !== null) {
        this.searchKeyword = String(value)
      }
      void this.loadApplications()
    },
    rowMatchesKeyword (row, kw) {
      if (!row || !kw) return true
      const userId = row.user_id != null ? String(row.user_id) : ''
      const username = row.username != null ? String(row.username) : ''
      const fullName = row.full_name != null ? String(row.full_name) : ''
      const school = row.school != null ? String(row.school) : ''
      const fields = [userId, username, fullName, school]
        .map((s) => s.trim().toLowerCase())
        .filter((s) => s && s !== '—')
      return fields.some((s) => s.indexOf(kw) >= 0)
    },
    parseList (res) {
      if (!res) return []
      const items = Array.isArray(res) ? res : (Array.isArray(res.items) ? res.items : [])
      return items
        .filter(row => row && row.user_id != null)
        .map(row => ({
          user_id: row.user_id,
          username: row.username || '—',
          email: row.email,
          full_name: row.full_name || '—',
          school: row.school || '—',
          application_status: row.application_status || 'not_submitted',
          application_contact: row.application_contact,
          application_remark: row.application_remark,
          application_submitted_at: row.application_submitted_at,
          school_admin_verified: row.school_admin_verified === true,
          review_feedback: row.review_feedback,
          reviewed_at: row.reviewed_at,
          photo_url: row.photo_url
        }))
    },
    async loadApplications () {
      this.listLoading = true
      try {
        const res = await listSchoolAdminApplications({
          status: this.statusFilter,
          keyword: (this.searchKeyword || '').trim() || undefined
        })
        this.applicationItems = this.parseList(res)
      } catch (e) {
        this.applicationItems = []
        this.$message.error('加载申请列表失败：' + this.getApiErrorMessage(e))
      } finally {
        this.listLoading = false
      }
    },
    revokePhotoModalUrl () {
      if (this.photoModalUrl) {
        URL.revokeObjectURL(this.photoModalUrl)
        this.photoModalUrl = null
      }
    },
    async openPhotoModal (record) {
      if (!record || record.user_id == null) return
      this.photoModalUserId = record.user_id
      this.photoModalVisible = true
      this.photoModalLoading = true
      this.revokePhotoModalUrl()
      try {
        const blob = await getSchoolAdminApplicationPhotoAdmin(record.user_id)
        if (blob && blob.size > 0) {
          this.photoModalUrl = URL.createObjectURL(blob)
        }
      } catch (e) {
        this.$message.error('加载照片失败：' + this.getApiErrorMessage(e))
      } finally {
        this.photoModalLoading = false
      }
    },
    closePhotoModal () {
      this.photoModalVisible = false
      this.photoModalUserId = null
      this.revokePhotoModalUrl()
    },
    async handleReview (record, action, feedback) {
      if (!record || record.user_id == null) return
      const userId = Number(record.user_id)
      this.reviewLoadingId = userId
      this.reviewAction = action
      try {
        await reviewSchoolAdminApplication(userId, {
          action,
          feedback: feedback != null ? feedback : undefined
        })
        this.$message.success(action === 'approve' ? '已通过审核' : '已驳回')
        await this.loadApplications()
      } catch (e) {
        this.$message.error('审核失败：' + this.getApiErrorMessage(e))
      } finally {
        this.reviewLoadingId = null
        this.reviewAction = null
      }
    },
    openRejectModal (record) {
      this.rejectModalRecord = record
      this.rejectFeedback = ''
      this.rejectModalVisible = true
    },
    closeRejectModal () {
      this.rejectModalVisible = false
      this.rejectModalRecord = null
      this.rejectFeedback = ''
      this.rejectModalLoading = false
    },
    async submitRejectModal () {
      if (!this.rejectModalRecord) return Promise.reject(new Error('cancelled'))
      this.rejectModalLoading = true
      try {
        await this.handleReview(
          this.rejectModalRecord,
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
.competition-school-admin-applications {
  width: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.page-toolbar {
  margin-bottom: 12px;
}

.photo-modal-img {
  display: block;
  max-width: 100%;
  max-height: 400px;
  margin: 0 auto;
}

.muted {
  color: rgba(0, 0, 0, 0.45);
}
</style>
