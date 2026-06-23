<template>
  <div class="competition-alt-register-root">
    <div
      id="competitionRegisterLayout"
      :class="['competition-user-layout-wrapper', device]"
    >
      <div class="container">
        <div class="top">
          <div class="header competition-auth-header">
            <span class="title">竞赛报名系统</span>
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
import { sanitizeCompetitionReturnPath } from '@/utils/competitionAuthFlow'

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
    registerSuccessNavigate () {
      const raw = this.$route.query.redirectAfterAlt
      const next = sanitizeCompetitionReturnPath(raw)
      if (next) {
        this.$router.push(next).catch(() => {})
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
  height: 100%;

  &.mobile .container .main {
    max-width: 368px;
    width: 98%;
  }

  .container {
    width: 100%;
    min-height: 100%;
    background: #f0f2f5 url(~@/assets/background.svg) no-repeat 50%;
    background-size: 100%;
    padding: 110px 0 144px;
    position: relative;

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
      height: 44px;
      line-height: 44px;

      .title {
        font-size: 33px;
        color: rgba(0, 0, 0, 0.85);
        font-family: Avenir, 'Helvetica Neue', Arial, Helvetica, sans-serif;
        font-weight: 600;
        position: relative;
        top: 2px;
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
    bottom: 0;
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
