<template>
  <div class="competition-detail-standalone-root">
    <div class="detail-back-bar">
      <div v-if="numericId" class="detail-toolbar-right">
        <!-- 未登录：登录 / 注册 -->
        <template v-if="!altLoggedIn">
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="openLoginModal">
            登录
          </a-button>
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="openRegisterModal">
            注册
          </a-button>
        </template>
        <!-- 已登录学生：报名 / 作品 / 退出 -->
        <template v-else-if="isCompetitionStudentRole">
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarEnroll">
            报名
          </a-button>
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarWorks">
            作品
          </a-button>
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarLogout">
            退出
          </a-button>
        </template>
        <!-- 已登录其他角色（指导老师等）：退出 -->
        <template v-else>
          <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarLogout">
            退出
          </a-button>
        </template>
      </div>
    </div>
    <a-alert
      v-if="!numericId"
      type="warning"
      show-icon
      message="缺少竞赛 ID"
      description="请从竞赛列表中点击「查看详情」进入，或使用管理员提供的竞赛链接。"
      style="margin: 0 0 16px"
    />
    <CompetitionRegistrationSystem
      v-else
      ref="registrationSys"
      standalone-detail-mode
      :share-link-mode="isShareLink"
      :share-guest-mode="shareGuestModeForChild"
      :initial-competition-id="numericId"
      :initial-view-division="initialViewDivision"
    />

    <a-modal
      v-model="showLoginModal"
      title="登录竞赛账号"
      :footer="null"
      width="420px"
      destroy-on-close
      wrap-class-name="standalone-competition-login-modal"
      @cancel="showLoginModal = false"
    >
      <p class="standalone-auth-hint">
        请使用竞赛报名系统独立账号登录。登录后将根据您的角色（学生 / 指导老师等）展示相应功能。
      </p>
      <ManuAltIdentityPanel mode="embedded" @session-changed="onLoginSuccess" />
    </a-modal>

    <a-modal
      v-model="showRegisterModal"
      title="注册竞赛账号"
      :footer="null"
      width="520px"
      destroy-on-close
      wrap-class-name="standalone-competition-register-modal"
      @cancel="showRegisterModal = false"
    >
      <p class="standalone-auth-hint">
        注册学生或指导老师账号后，请使用同一账号登录以报名或组班。
      </p>
      <ManuAltIdentityRegisterPanel
        mode="embedded"
        @register-success="onRegisterSuccess"
        @switch-to-login="switchToLoginFromRegister"
      />
    </a-modal>
  </div>
</template>

<script>
import CompetitionRegistrationSystem from '@/views/manus/CompetitionRegistrationSystem.vue'
import ManuAltIdentityPanel from '@/views/manus/ManuAltIdentityPanel.vue'
import ManuAltIdentityRegisterPanel from '@/views/manus/ManuAltIdentityRegisterPanel.vue'
import {
  getStoredAltToken,
  isAltCompetitionStudent,
  clearAltIdentityStorage
} from '@/api/altIdentity'

export default {
  name: 'CompetitionDetailStandalone',
  components: { CompetitionRegistrationSystem, ManuAltIdentityPanel, ManuAltIdentityRegisterPanel },
  data () {
    return {
      /** 独立账号写入 localStorage 后触发重算登录态与角色 */
      toolbarIdentityTick: 0,
      showLoginModal: false,
      showRegisterModal: false,
      /** 分享链接页：本会话内是否已通过弹窗登录 */
      shareSessionActive: false
    }
  },
  created () {
    this.initShareLinkGuestSession()
  },
  mounted () {
    window.addEventListener('alt-identity-changed', this.bumpToolbarIdentityTick)
  },
  beforeDestroy () {
    window.removeEventListener('alt-identity-changed', this.bumpToolbarIdentityTick)
  },
  methods: {
    bumpToolbarIdentityTick () {
      this.toolbarIdentityTick += 1
    },
    /** 分享链接（share=1）：首次进入清除本地独立账号，保证默认未登录 */
    initShareLinkGuestSession () {
      if (!this.isShareLink) return
      const key = this.shareSessionStorageKey
      const active = !!sessionStorage.getItem(key)
      this.shareSessionActive = active
      if (!active) {
        clearAltIdentityStorage()
      }
    },
    openLoginModal () {
      this.showRegisterModal = false
      this.showLoginModal = true
    },
    openRegisterModal () {
      this.showLoginModal = false
      this.showRegisterModal = true
    },
    switchToLoginFromRegister () {
      this.showRegisterModal = false
      this.showLoginModal = true
    },
    onRegisterSuccess ({ role }) {
      this.showRegisterModal = false
      if (role === 'expert') return
      this.$message.success('注册成功，请登录')
      this.showLoginModal = true
    },
    onLoginSuccess () {
      this.showLoginModal = false
      if (this.isShareLink) {
        sessionStorage.setItem(this.shareSessionStorageKey, '1')
        this.shareSessionActive = true
      }
      this.bumpToolbarIdentityTick()
      this.$nextTick(() => {
        const sys = this.$refs.registrationSys
        if (sys && typeof sys.bootstrapStandaloneDetail === 'function') {
          void sys.bootstrapStandaloneDetail()
        }
      })
    },
    onToolbarLogout () {
      if (this.isShareLink) {
        sessionStorage.removeItem(this.shareSessionStorageKey)
        this.shareSessionActive = false
      }
      clearAltIdentityStorage()
      this.bumpToolbarIdentityTick()
      this.$message.success('已退出登录')
      this.$nextTick(() => {
        const sys = this.$refs.registrationSys
        if (sys && typeof sys.bootstrapStandaloneDetail === 'function') {
          void sys.bootstrapStandaloneDetail()
        }
      })
    },
    onToolbarEnroll () {
      const c = this.$refs.registrationSys
      if (c && typeof c.openStandaloneEnrollModal === 'function') {
        c.openStandaloneEnrollModal()
      }
    },
    onToolbarWorks () {
      const c = this.$refs.registrationSys
      if (c && typeof c.openStandaloneMyWorksModal === 'function') {
        c.openStandaloneMyWorksModal()
      }
    }
  },
  computed: {
    numericId () {
      const q = this.$route.query.id
      if (q == null || String(q).trim() === '') return null
      const n = Number(q)
      return Number.isFinite(n) && n > 0 ? n : null
    },
    initialViewDivision () {
      const d = this.$route.query.division
      if (d === 'undergraduate' || d === 'vocational') return d
      return null
    },
    /** 超级管理员复制的分享链接带 share=1，默认以未登录访客进入 */
    isShareLink () {
      const s = this.$route.query.share
      return s === '1' || s === 1 || s === true || s === 'true'
    },
    shareSessionStorageKey () {
      const id = this.numericId != null ? String(this.numericId) : 'x'
      const div = this.initialViewDivision || ''
      return `competition_share_authed_${id}_${div}`
    },
    altLoggedIn () {
      void this.toolbarIdentityTick
      if (this.isShareLink) {
        return this.shareSessionActive && !!getStoredAltToken()
      }
      return !!getStoredAltToken()
    },
    shareGuestModeForChild () {
      return this.isShareLink && !this.shareSessionActive
    },
    isCompetitionStudentRole () {
      void this.toolbarIdentityTick
      if (getStoredAltToken()) return isAltCompetitionStudent()
      const roles = this.$store.getters.roles || []
      return roles.includes('student')
    }
  }
}
</script>

<style scoped>
.competition-detail-standalone-root {
  min-height: 100vh;
  padding: 16px;
  box-sizing: border-box;
  background-color: #0a0618;
  background-image: url('~@/assets/背景图.jpeg');
  background-repeat: no-repeat;
  background-position: center;
  background-size: cover;
}

.detail-back-bar {
  margin: 0 0 12px;
  padding: 4px 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 12px 16px;
}

.detail-toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.detail-toolbar-btn {
  height: 32px;
}

.standalone-auth-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  line-height: 1.5;
}
</style>
