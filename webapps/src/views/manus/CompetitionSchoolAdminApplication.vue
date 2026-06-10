<template>
  <div class="competition-school-admin-application">
    <a-card :bordered="false" class="section-card">
      <a-alert type="info" show-icon message="校管理员资料申请" style="margin-bottom: 16px">
        <template slot="description">
          注册为校管理员后可登录。须提交资料（含照片）并经超级管理员审核通过后，方可前往「校审」审核本校组队。
        </template>
      </a-alert>

      <a-card size="small" title="资料申请" :bordered="true" class="sub-block">
        <a-spin :spinning="applicationLoading">
          <a-descriptions v-if="application" bordered size="small" :column="1" style="margin-bottom: 16px">
            <a-descriptions-item label="学校">{{ application.school || '—' }}</a-descriptions-item>
            <a-descriptions-item label="姓名">{{ application.full_name || '—' }}</a-descriptions-item>
            <a-descriptions-item label="申请状态">
              <span
                v-if="isApplicationNotSubmitted"
                class="application-status-text application-status-text--not-submitted"
              >{{ applicationStatusText }}</span>
              <a-tag v-else :color="applicationStatusColor">{{ applicationStatusText }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item v-if="application.application_contact" label="联系方式">
              {{ application.application_contact }}
            </a-descriptions-item>
            <a-descriptions-item v-if="application.application_remark" label="申请备注">
              {{ application.application_remark }}
            </a-descriptions-item>
            <a-descriptions-item v-if="application.application_submitted_at" label="提交时间">
              {{ formatDateTime(application.application_submitted_at) }}
            </a-descriptions-item>
            <a-descriptions-item v-if="application.review_feedback" label="审核反馈">
              {{ application.review_feedback }}
            </a-descriptions-item>
            <a-descriptions-item v-if="application.reviewed_at" label="审核时间">
              {{ formatDateTime(application.reviewed_at) }}
            </a-descriptions-item>
          </a-descriptions>

          <div v-if="photoPreviewUrl" class="photo-preview-block">
            <div class="photo-preview-label">申请照片</div>
            <img :src="photoPreviewUrl" alt="申请照片" class="photo-preview-img" />
          </div>

          <a-form
            v-if="canSubmitApplication"
            layout="vertical"
            class="application-form"
            style="max-width: 520px"
          >
            <a-form-item label="申请照片" required>
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                @change="onPhotoFileChange"
              />
              <div v-if="applicationPhotoFile" class="muted" style="margin-top: 6px">
                已选择：{{ applicationPhotoFile.name }}
              </div>
              <div class="muted" style="margin-top: 4px; font-size: 12px">
                支持 png/jpg/jpeg/gif/webp，不超过 5MB
              </div>
            </a-form-item>
            <a-form-item label="联系方式">
              <a-input v-model="applicationForm.contact" placeholder="手机或邮箱，选填" />
            </a-form-item>
            <a-form-item label="申请备注">
              <a-textarea v-model="applicationForm.remark" :rows="3" placeholder="选填" />
            </a-form-item>
            <a-button type="primary" :loading="submitApplicationLoading" @click="handleSubmitApplication">
              提交资料申请
            </a-button>
          </a-form>

          <a-alert
            v-else-if="application && application.application_status === 'pending'"
            type="warning"
            show-icon
            message="资料审核中"
            description="您的申请已提交，请等待超级管理员审核。审核通过前无法使用「校审」功能。"
          />

          <a-alert
            v-else-if="application && application.application_status === 'approved'"
            type="success"
            show-icon
            message="资料已通过审核"
            description="您可前往左侧「校审」执行组队校审操作。"
          />
        </a-spin>
      </a-card>
    </a-card>
  </div>
</template>

<script>
import {
  getSchoolAdminApplicationMe,
  submitSchoolAdminApplication,
  getSchoolAdminApplicationPhoto
} from '@/api/competition'
import { fetchAltIdentityMe, applyAltIdentityMeToStorage } from '@/api/altIdentity'

const APPLICATION_STATUS_MAP = {
  not_submitted: { text: '未提交', color: 'default' },
  pending: { text: '审核中', color: 'orange' },
  approved: { text: '已通过', color: 'green' },
  rejected: { text: '已驳回', color: 'red' }
}

export default {
  name: 'CompetitionSchoolAdminApplication',
  data () {
    return {
      applicationLoading: false,
      application: null,
      applicationPhotoFile: null,
      applicationForm: {
        contact: '',
        remark: ''
      },
      submitApplicationLoading: false,
      photoPreviewUrl: null
    }
  },
  computed: {
    applicationStatusText () {
      const s = this.application && this.application.application_status
      return (APPLICATION_STATUS_MAP[s] || { text: s || '—' }).text
    },
    applicationStatusColor () {
      const s = this.application && this.application.application_status
      return (APPLICATION_STATUS_MAP[s] || { color: 'default' }).color
    },
    isApplicationNotSubmitted () {
      const s = this.application && this.application.application_status
      return s === 'not_submitted' || !s
    },
    canSubmitApplication () {
      if (!this.application) return true
      const s = this.application.application_status
      return s === 'not_submitted' || s === 'rejected' || !s
    }
  },
  mounted () {
    void this.loadApplication()
  },
  beforeDestroy () {
    this.revokePhotoPreview()
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
    revokePhotoPreview () {
      if (this.photoPreviewUrl) {
        URL.revokeObjectURL(this.photoPreviewUrl)
        this.photoPreviewUrl = null
      }
    },
    async loadPhotoPreview () {
      this.revokePhotoPreview()
      if (!this.application || !this.application.photo_url) return
      try {
        const blob = await getSchoolAdminApplicationPhoto()
        if (blob && blob.size > 0) {
          this.photoPreviewUrl = URL.createObjectURL(blob)
        }
      } catch (e) {
        /* 照片可能尚未上传 */
      }
    },
    parseApplication (res) {
      if (!res || typeof res !== 'object') return null
      return {
        user_id: res.user_id,
        school: res.school,
        full_name: res.full_name,
        school_admin_verified: res.school_admin_verified === true,
        application_status: res.application_status || 'not_submitted',
        application_contact: res.application_contact,
        application_remark: res.application_remark,
        application_submitted_at: res.application_submitted_at,
        review_feedback: res.review_feedback,
        reviewed_at: res.reviewed_at,
        photo_url: res.photo_url,
        can_review_teams: res.can_review_teams === true
      }
    },
    async loadApplication () {
      this.applicationLoading = true
      try {
        const res = await getSchoolAdminApplicationMe()
        this.application = this.parseApplication(res)
        if (this.application && this.application.application_contact) {
          this.applicationForm.contact = this.application.application_contact
        }
        if (this.application && this.application.application_remark) {
          this.applicationForm.remark = this.application.application_remark
        }
        await this.loadPhotoPreview()
      } catch (e) {
        this.application = null
        this.$message.error('加载申请状态失败：' + this.getApiErrorMessage(e))
      } finally {
        this.applicationLoading = false
      }
    },
    onPhotoFileChange (e) {
      const file = e && e.target && e.target.files ? e.target.files[0] : null
      this.applicationPhotoFile = file || null
    },
    async handleSubmitApplication () {
      if (!this.applicationPhotoFile) {
        this.$message.warning('请上传申请照片')
        return
      }
      const maxBytes = 5 * 1024 * 1024
      if (this.applicationPhotoFile.size > maxBytes) {
        this.$message.warning('照片不能超过 5MB')
        return
      }
      const fd = new FormData()
      fd.append('photo', this.applicationPhotoFile)
      const contact = (this.applicationForm.contact || '').trim()
      const remark = (this.applicationForm.remark || '').trim()
      if (contact) fd.append('contact', contact)
      if (remark) fd.append('remark', remark)

      this.submitApplicationLoading = true
      try {
        const res = await submitSchoolAdminApplication(fd)
        this.application = this.parseApplication(res)
        this.applicationPhotoFile = null
        this.$message.success('资料申请已提交，请等待超级管理员审核')
        await this.loadPhotoPreview()
        try {
          const me = await fetchAltIdentityMe()
          applyAltIdentityMeToStorage(me)
        } catch (syncErr) {
          /* 非关键 */
        }
      } catch (e) {
        this.$message.error('提交失败：' + this.getApiErrorMessage(e))
      } finally {
        this.submitApplicationLoading = false
      }
    }
  }
}
</script>

<style scoped lang="less">
.competition-school-admin-application {
  width: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.sub-block {
  background: #fafafa;
}

.application-form {
  margin-top: 8px;
}

.photo-preview-block {
  margin-bottom: 16px;
}

.photo-preview-label {
  margin-bottom: 8px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
}

.photo-preview-img {
  max-width: 240px;
  max-height: 240px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.muted {
  color: rgba(0, 0, 0, 0.45);
}

.application-status-text--not-submitted {
  color: rgba(0, 0, 0, 0.85);
  font-size: 14px;
}
</style>
