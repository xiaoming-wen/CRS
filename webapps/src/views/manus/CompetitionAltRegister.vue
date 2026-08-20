<template>
  <div class="competition-alt-register-root">
    <div
      id="competitionRegisterLayout"
      :class="['competition-user-layout-wrapper', device]"
    >
      <div class="container">
        <div class="top">
          <div class="header competition-auth-header">
            <span class="title">合肥大学AI竞赛报名系统</span>
          </div>
        </div>

        <div class="main">
          <ManuAltIdentityRegisterPanel @register-success="registerSuccessNavigate" />
        </div>

        <div class="footer">
          <div class="links">
            <a href="_self">帮助</a>
            <a href="_self">隐私</a>
            <a href="_self">条款</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mixinDevice } from '@/utils/mixin'
import ManuAltIdentityRegisterPanel from '@/views/manus/ManuAltIdentityRegisterPanel.vue'
import {
  sanitizeCompetitionReturnPath,
  getStudentAdvisorLandingFullPath
} from '@/utils/competitionAuthFlow'

export default {
  name: 'CompetitionAltRegister',
  components: { ManuAltIdentityRegisterPanel },
  mixins: [mixinDevice],
  mounted () {
    document.body.classList.add('userLayout')
  },
  beforeDestroy () {
    document.body.classList.remove('userLayout')
  },
  methods: {
    registerSuccessNavigate (payload) {
      const role = payload && payload.role != null ? String(payload.role) : ''
      const raw = this.$route.query.redirectAfterAlt
      let next = sanitizeCompetitionReturnPath(raw)
      if (!next && (role === 'student' || role === 'advisor')) {
        next = getStudentAdvisorLandingFullPath()
      }
      // 注册不自动登录：回到主页登录，登录成功后再进竞赛详情
      if (next) {
        this.$router.push({
          name: 'ManuVideoCompetition',
          query: { redirectAfterAlt: next }
        }).catch(() => {})
        return
      }
      this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
    }
  }
}
</script>

<style scoped lang="less">
.competition-alt-register-root {
  min-height: 100vh;
}

.competition-user-layout-wrapper {
  min-height: 100vh;
  height: 100%;

  &.mobile .container .main {
    max-width: 368px;
    width: 98%;
  }

  .container {
    width: 100%;
    min-height: 100vh;
    background: #f0f2f5 url(~@/assets/background.svg) no-repeat center center;
    background-size: cover;
    padding: 110px 0 144px;
    position: relative;
    box-sizing: border-box;

    a {
      text-decoration: none;
    }
  }

  .competition-auth-header .title {
    display: inline-block;
  }

  .top {
    text-align: center;

    .header {
      height: auto;
      min-height: 44px;
      line-height: 1.3;

      .title {
        font-size: 28px;
        color: rgba(0, 0, 0, 0.85);
        font-family: Avenir, 'Helvetica Neue', Arial, Helvetica, sans-serif;
        font-weight: 600;
        position: relative;
        top: 2px;
        max-width: 92vw;
        padding: 0 12px;
      }
    }
  }

  .main {
    min-width: 260px;
    width: 368px;
    margin: 0 auto;
  }

  .footer {
    position: absolute;
    width: 100%;
    bottom: 40px;
    padding: 0 16px;
    margin: 48px 0 24px;
    text-align: center;

    .links {
      margin-bottom: 8px;
      font-size: 14px;

      a {
        color: rgba(0, 0, 0, 0.45);
        transition: all 0.3s;

        &:not(:last-child) {
          margin-right: 40px;
        }
      }
    }
  }
}
</style>
