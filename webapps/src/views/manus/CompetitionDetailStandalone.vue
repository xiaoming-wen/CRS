<template>
  <div class="competition-detail-standalone-root">
    <div v-if="showDetailTopBar" class="detail-back-bar">
      <a-button
        v-if="showStandaloneBackButton"
        type="link"
        class="back-to-list-btn"
        @click="goToCompetitionList"
      >
        <a-icon type="left" />
        返回竞赛列表
      </a-button>
      <div
        v-if="detailLogoUrl"
        class="detail-logo-wrap"
        :class="{ 'detail-logo-wrap--after-back': showStandaloneBackButton }"
      >
        <img :src="detailLogoUrl" alt="竞赛 Logo" class="detail-logo-img">
      </div>
      <div v-if="showStandaloneGuestToolbar" class="detail-toolbar-right">
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="goMainLogin">
          登录
        </a-button>
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="goMainRegister">
          注册
        </a-button>
      </div>
      <div v-else-if="showStandaloneStudentToolbar" class="detail-toolbar-right">
        <a-button
          v-if="showExamPaperDownloadToolbar"
          type="primary"
          ghost
          class="detail-toolbar-btn"
          :loading="examPaperToolbarLoading"
          @click="onToolbarDownloadExamPaper"
        >
          下载试卷
        </a-button>
        <a-button
          v-if="showEnrollToolbar"
          type="primary"
          ghost
          class="detail-toolbar-btn"
          @click="onToolbarEnroll"
        >
          {{ enrollToolbarLabel }}
        </a-button>
        <a-button
          v-if="showSubmitWorksToolbar"
          type="primary"
          ghost
          class="detail-toolbar-btn"
          @click="onToolbarWorks"
        >
          提交作品
        </a-button>
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarLogout">
          退出
        </a-button>
      </div>
      <div v-else-if="showStandaloneAdvisorToolbar" class="detail-toolbar-right">
        <a-button
          v-if="showExamPaperDownloadToolbar"
          type="primary"
          ghost
          class="detail-toolbar-btn"
          :loading="examPaperToolbarLoading"
          @click="onToolbarDownloadExamPaper"
        >
          下载试卷
        </a-button>
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarLogout">
          退出
        </a-button>
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
      @exam-papers-changed="bumpToolbarIdentityTick"
      @enroll-block-changed="onEnrollBlockChanged"
    />
  </div>
</template>

<script>
import CompetitionRegistrationSystem from '@/views/manus/CompetitionRegistrationSystem.vue'
import {
  getStoredAltToken,
  isAltCompetitionStudent,
  isAltCompetitionSuperAdmin,
  isAltCompetitionExpert,
  isAltCompetitionAdvisorOrTeacher,
  clearAltIdentityStorage,
  markAltLoginSkipAutoOnce,
  fetchAltIdentityMe,
  applyAltIdentityMeToStorage
} from '@/api/altIdentity'
import { buildAbsoluteRouteUrl } from '@/utils/openRouteInNewTab'
import { getCompetitionLogo } from '@/api/competition'
import { markCompetitionShareSessionAuthed, getStudentAdvisorLandingFullPath } from '@/utils/competitionAuthFlow'

export default {
  name: 'CompetitionDetailStandalone',
  components: { CompetitionRegistrationSystem },
  data () {
    return {
      /** 独立账号写入 localStorage 后触发重算登录态与角色 */
      toolbarIdentityTick: 0,
      /** 分享链接页：本会话内是否已通过主页登录 */
      shareSessionActive: false,
      examPaperToolbarLoading: false,
      /** 子组件报名成功后同步，用于顶栏「提交作品」显示 */
      childHasEnrollment: false,
      /** 当前是否决赛阶段（决赛不显示报名入口） */
      childIsFinalStage: false,
      detailLogoUrl: null,
      detailLogoLoadSeq: 0
    }
  },
  created () {
    this.initShareLinkGuestSession()
  },
  mounted () {
    window.addEventListener('alt-identity-changed', this.bumpToolbarIdentityTick)
    this.$nextTick(() => {
      void this.ensureWorkbenchDetailAutoSession()
      void this.ensureShareLoggedInBootstrap()
      void this.loadDetailLogo()
    })
  },
  beforeDestroy () {
    window.removeEventListener('alt-identity-changed', this.bumpToolbarIdentityTick)
    this.clearDetailLogo()
  },
  watch: {
    numericId () {
      void this.loadDetailLogo()
    }
  },
  methods: {
    clearDetailLogo () {
      this.detailLogoLoadSeq += 1
      if (this.detailLogoUrl) {
        try {
          URL.revokeObjectURL(this.detailLogoUrl)
        } catch (e) { /* noop */ }
      }
      this.detailLogoUrl = null
    },
    async loadDetailLogo () {
      const id = this.numericId
      if (!id) {
        this.clearDetailLogo()
        return
      }
      const seq = ++this.detailLogoLoadSeq
      try {
        const blob = await getCompetitionLogo(id)
        if (seq !== this.detailLogoLoadSeq) return
        if (!blob || typeof blob.size !== 'number' || blob.size <= 0) {
          this.clearDetailLogo()
          return
        }
        const t = (blob.type || '').toLowerCase()
        if (t.includes('json') || t.includes('html') || t.includes('text/plain')) {
          this.clearDetailLogo()
          return
        }
        if (this.detailLogoUrl) {
          try {
            URL.revokeObjectURL(this.detailLogoUrl)
          } catch (e) { /* noop */ }
        }
        this.detailLogoUrl = URL.createObjectURL(blob)
      } catch (e) {
        if (seq !== this.detailLogoLoadSeq) return
        this.clearDetailLogo()
      }
    },
    bumpToolbarIdentityTick () {
      this.toolbarIdentityTick += 1
    },
    onEnrollBlockChanged (payload) {
      if (payload && typeof payload === 'object') {
        this.childHasEnrollment = !!(
          payload.hasAnyEnrollment ||
          payload.myEnrolledTeam ||
          payload.myEnrolledIndividual
        )
        this.childIsFinalStage = !!(payload.isFinal || payload.stage === 'final')
      } else {
        const c = this.$refs.registrationSys
        this.childHasEnrollment = !!(
          c && (c.hasAnyEnrollment || c.myEnrolledTeam || c.myEnrolledIndividual)
        )
        this.childIsFinalStage = !!(c && c.isActiveCompetitionFinal)
      }
      this.bumpToolbarIdentityTick()
    },
    /** 分享链接（share=1）：有令牌则视为已登录；无令牌才进访客态（不清掉刚写入的登录令牌） */
    initShareLinkGuestSession () {
      if (!this.isShareLink) return
      const key = this.shareSessionStorageKey
      const hasToken = !!getStoredAltToken()
      if (hasToken) {
        try {
          sessionStorage.setItem(key, '1')
        } catch (e) { /* ignore */ }
        markCompetitionShareSessionAuthed(this.numericId, this.initialViewDivision || '')
        this.shareSessionActive = true
        return
      }
      try {
        sessionStorage.removeItem(key)
      } catch (e) { /* ignore */ }
      this.shareSessionActive = false
    },
    /** 详情页访客：改走主页登录（不再弹窗） */
    goMainLogin () {
      const returnPath = this.$route.fullPath || getStudentAdvisorLandingFullPath()
      this.$router.push({
        name: 'ManuVideoCompetition',
        query: { redirectAfterAlt: returnPath }
      }).catch(() => {})
    },
    goMainRegister () {
      const returnPath = this.$route.fullPath || getStudentAdvisorLandingFullPath()
      this.$router.push({
        name: 'ManuVideoCompetitionRegister',
        query: { redirectAfterAlt: returnPath }
      }).catch(() => {})
    },
    onToolbarLogout () {
      if (this.isShareLink) {
        try {
          sessionStorage.removeItem(this.shareSessionStorageKey)
        } catch (e) { /* ignore */ }
        this.shareSessionActive = false
      }
      markAltLoginSkipAutoOnce()
      clearAltIdentityStorage()
      this.childHasEnrollment = false
      this.bumpToolbarIdentityTick()
      this.$message.success('已退出登录，请重新登录')
      // 回到主页面登录门禁
      this.$router.replace({ name: 'ManuVideoCompetition' }).catch(() => {})
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
    },
    onToolbarDownloadExamPaper () {
      const c = this.$refs.registrationSys
      if (!c || typeof c.downloadActiveExamPaper !== 'function') return
      this.examPaperToolbarLoading = true
      Promise.resolve(c.downloadActiveExamPaper())
        .catch(() => {})
        .finally(() => {
          this.examPaperToolbarLoading = false
        })
    },
    goToCompetitionList () {
      const listHref = this.resolveCompetitionListHref()
      const listHash = '#/manu/competition-list'

      try {
        if (window.opener && typeof window.opener.focus === 'function' && !window.opener.closed) {
          try {
            if (listHref) {
              window.opener.location.assign(listHref)
            } else {
              window.opener.location.hash = listHash
            }
          } catch (e) {
            /* 跨域等 */
          }
          window.opener.focus()
          window.close()
          return
        }
      } catch (e) {
        /* ignore */
      }

      if (listHref) {
        window.location.assign(listHref)
      } else {
        window.location.hash = listHash
      }
    },
    resolveCompetitionListHref () {
      try {
        return buildAbsoluteRouteUrl(this.$router, { path: '/manu/competition-list' })
      } catch (e) {
        return null
      }
    },
    /** 从竞赛列表打开详情页时，超级管理员/专家沿用列表页已登录的独立账号 */
    async ensureWorkbenchDetailAutoSession () {
      if (!this.numericId || !this.isFromCompetitionList || this.isShareLink) return
      if (!this.isWorkbenchDetailRole || !getStoredAltToken()) return
      try {
        const me = await fetchAltIdentityMe()
        applyAltIdentityMeToStorage(me)
        this.bumpToolbarIdentityTick()
        const sys = this.$refs.registrationSys
        if (sys && typeof sys.bootstrapStandaloneDetail === 'function') {
          await sys.bootstrapStandaloneDetail()
        }
      } catch (e) {
        const msg = e && e.message ? e.message : ''
        if (msg) console.warn('[CompetitionDetailStandalone] workbench auto session failed:', msg)
      }
    },
    /** 主页登录后进入 share 详情：同步资料并按已登录态加载报名/组队能力 */
    async ensureShareLoggedInBootstrap () {
      if (!this.numericId || !this.isShareLink || !this.altLoggedIn) return
      try {
        if (getStoredAltToken()) {
          const me = await fetchAltIdentityMe()
          applyAltIdentityMeToStorage(me)
          this.bumpToolbarIdentityTick()
        }
        const sys = this.$refs.registrationSys
        if (sys && typeof sys.bootstrapStandaloneDetail === 'function') {
          await sys.bootstrapStandaloneDetail()
        }
        this.onEnrollBlockChanged()
      } catch (e) {
        const msg = e && e.message ? e.message : ''
        if (msg) console.warn('[CompetitionDetailStandalone] share login bootstrap failed:', msg)
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
    /** 由竞赛列表「查看详情」打开（非分享链接复制） */
    isFromCompetitionList () {
      const v = this.$route.query.fromList
      return v === '1' || v === 1 || v === true || v === 'true'
    },
    shareSessionStorageKey () {
      const id = this.numericId != null ? String(this.numericId) : 'x'
      const div = this.initialViewDivision || ''
      return `competition_share_authed_${id}_${div}`
    },
    altLoggedIn () {
      void this.toolbarIdentityTick
      if (this.isShareLink && !this.isFromCompetitionList) {
        return this.shareSessionActive && !!getStoredAltToken()
      }
      return !!getStoredAltToken()
    },
    shareGuestModeForChild () {
      if (this.isFromCompetitionList) return false
      return this.isShareLink && !this.shareSessionActive
    },
    isCompetitionStudentRole () {
      void this.toolbarIdentityTick
      if (getStoredAltToken()) return isAltCompetitionStudent()
      const roles = this.$store.getters.roles || []
      return roles.includes('student')
    },
    isWorkbenchDetailRole () {
      void this.toolbarIdentityTick
      if (getStoredAltToken()) {
        return isAltCompetitionSuperAdmin() || isAltCompetitionExpert()
      }
      const roles = this.$store.getters.roles || []
      return roles.includes('super_admin')
    },
    isAdvisorOrTeacherRole () {
      void this.toolbarIdentityTick
      if (getStoredAltToken()) return isAltCompetitionAdvisorOrTeacher()
      const roles = this.$store.getters.roles || []
      return roles.includes('advisor') || roles.includes('teacher')
    },
    showStandaloneBackButton () {
      return (
        this.numericId != null &&
        this.isFromCompetitionList &&
        this.isWorkbenchDetailRole &&
        !this.isCompetitionStudentRole &&
        !this.isAdvisorOrTeacherRole
      )
    },
    showStandaloneGuestToolbar () {
      return this.numericId != null && this.isShareLink && !this.altLoggedIn
    },
    showStandaloneStudentToolbar () {
      return this.numericId != null && this.isCompetitionStudentRole && this.altLoggedIn
    },
    showStandaloneAdvisorToolbar () {
      return (
        this.numericId != null &&
        this.isAdvisorOrTeacherRole &&
        !this.isCompetitionStudentRole &&
        this.altLoggedIn
      )
    },
    showExamPaperDownloadToolbar () {
      void this.toolbarIdentityTick
      const c = this.$refs.registrationSys
      return !!(c && c.canShowExamPaperDownload)
    },
    /** 决赛不开放报名；已晋级可打开「我的队伍」查看信息 */
    showEnrollToolbar () {
      void this.toolbarIdentityTick
      if (this.childIsFinalStage) {
        return !!this.childHasEnrollment
      }
      const c = this.$refs.registrationSys
      if (c && c.isActiveCompetitionFinal) {
        return !!(c.hasAnyEnrollment || c.myEnrolledTeam)
      }
      return true
    },
    enrollToolbarLabel () {
      void this.toolbarIdentityTick
      if (this.childIsFinalStage || (this.$refs.registrationSys && this.$refs.registrationSys.isActiveCompetitionFinal)) {
        return '我的队伍'
      }
      return '报名'
    },
    /** 报名成功后才显示「提交作品」 */
    showSubmitWorksToolbar () {
      void this.toolbarIdentityTick
      if (this.childHasEnrollment) return true
      const c = this.$refs.registrationSys
      if (!c) return false
      return !!(c.hasAnyEnrollment || c.myEnrolledTeam || c.myEnrolledIndividual)
    },
    showDetailTopBar () {
      return (
        !!this.detailLogoUrl ||
        this.showStandaloneBackButton ||
        this.showStandaloneGuestToolbar ||
        this.showStandaloneStudentToolbar ||
        this.showStandaloneAdvisorToolbar
      )
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
  margin: 0 -16px 12px;
  padding: 4px 0 4px 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 16px;
  width: calc(100% + 32px);
  box-sizing: border-box;
}

.detail-logo-wrap {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  max-width: min(280px, 46vw);
}

/* 超管/专家：顶栏右侧靠右，略向左留白 */
.detail-logo-wrap--after-back {
  margin-left: auto;
  margin-right: 24px;
}

.detail-logo-img {
  display: block;
  max-height: 44px;
  max-width: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}

.detail-toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
  padding-right: 16px;
}

.detail-toolbar-btn {
  height: 32px;
  color: #fff !important;
  background: #1a1843 !important;
  border-color: #1a1843 !important;
  text-shadow: none;
}

.detail-toolbar-btn:hover,
.detail-toolbar-btn:focus {
  color: #fff !important;
  background: #24225a !important;
  border-color: #24225a !important;
}

.detail-toolbar-btn:active {
  color: #fff !important;
  background: #100e2e !important;
  border-color: #100e2e !important;
}

.back-to-list-btn {
  padding-left: 0;
  height: auto;
  font-size: 15px;
  color: #fff !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}

.back-to-list-btn:hover,
.back-to-list-btn:focus {
  color: rgba(255, 255, 255, 0.88) !important;
}

.back-to-list-btn ::v-deep .anticon {
  color: inherit;
}

.standalone-auth-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  line-height: 1.5;
}
</style>
