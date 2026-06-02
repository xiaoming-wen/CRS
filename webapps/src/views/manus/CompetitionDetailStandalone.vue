<template>
  <div class="competition-detail-standalone-root">
    <div class="detail-back-bar">
      <a-button type="link" class="back-to-list-btn" @click="goToCompetitionList">
        <a-icon type="left" />
        返回竞赛列表
      </a-button>
      <div v-if="showStandaloneStudentToolbar" class="detail-toolbar-right">
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarEnroll">
          报名
        </a-button>
        <a-button type="primary" ghost class="detail-toolbar-btn" @click="onToolbarWorks">
          作品
        </a-button>
      </div>
    </div>
    <a-alert
      v-if="!numericId"
      type="warning"
      show-icon
      message="缺少竞赛 ID"
      description="请从竞赛列表中点击「查看详情」进入。"
      style="margin: 0 0 16px"
    />
    <CompetitionRegistrationSystem
      v-else
      ref="registrationSys"
      standalone-detail-mode
      :initial-competition-id="numericId"
      :initial-view-division="initialViewDivision"
    />
  </div>
</template>

<script>
import CompetitionRegistrationSystem from '@/views/manus/CompetitionRegistrationSystem.vue'
import { getStoredAltToken, isAltCompetitionStudent } from '@/api/altIdentity'

export default {
  name: 'CompetitionDetailStandalone',
  components: { CompetitionRegistrationSystem },
  data () {
    return {
      /** 独立账号写入 localStorage 后触发重算「是否学生」 */
      toolbarIdentityTick: 0
    }
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
    /** 竞赛列表完整 URL（整页跳转，避免仅在当前页内 router.push） */
    resolveCompetitionListHref () {
      try {
        const r = this.$router.resolve({ path: '/manu/competition-list' })
        return r && r.href ? r.href : null
      } catch (e) {
        return null
      }
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
    goToCompetitionList () {
      const listHref = this.resolveCompetitionListHref()
      const listHash = '#/manu/competition-list'

      // 从列表点「查看详情」打开的本页：回到原浏览器标签的竞赛列表，并关闭当前详情标签（非当前页内切路由）
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

      // 无 opener：整页跳转到竞赛列表（不用 router.push，等同新开/刷新到列表页）
      if (listHref) {
        window.location.assign(listHref)
      } else {
        window.location.hash = listHash
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
    /** 与 CompetitionRegistrationSystem 中 isStudent 一致：竞赛独立账号按资料 role；否则主站 roles */
    isCompetitionStudentRole () {
      void this.toolbarIdentityTick
      if (getStoredAltToken()) return isAltCompetitionStudent()
      const roles = this.$store.getters.roles || []
      return roles.includes('student')
    },
    showStandaloneStudentToolbar () {
      return this.numericId != null && this.isCompetitionStudentRole
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
  flex-wrap: wrap;
  gap: 12px 16px;
}

.detail-toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.detail-toolbar-btn {
  height: 32px;
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
</style>
