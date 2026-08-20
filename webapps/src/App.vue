<template>
  <a-config-provider :locale="locale">
    <div id="app" :class="{ 'app--competition-detail': isCompetitionDetailPage }">
      <div class="app-main">
        <router-view />
      </div>
      <footer class="site-beian-footer" :class="{ 'site-beian-footer--dark': isCompetitionDetailPage }">
        <a
          href="https://beian.mps.gov.cn"
          target="_blank"
          rel="noopener noreferrer"
        >皖公网安备34019102001538号</a>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
        >皖ICP备05002535号</a>
      </footer>
    </div>
  </a-config-provider>
</template>

<script>
import zhCN from 'ant-design-vue/lib/locale-provider/zh_CN'
import { AppDeviceEnquire } from '@/utils/mixin'

export default {
  mixins: [AppDeviceEnquire],
  data () {
    return {
      locale: zhCN
    }
  },
  computed: {
    isCompetitionDetailPage () {
      const name = this.$route && this.$route.name
      const path = (this.$route && this.$route.path) || ''
      return name === 'ManuCompetitionDetail' || path.indexOf('/manu/competition-detail') === 0
    }
  }
}
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
}

.app-main {
  min-height: 100%;
  /* 避免内容被底部备案栏遮挡 */
  padding-bottom: 40px;
  box-sizing: border-box;
}

/* 竞赛详情：整页底色与详情页一致，避免底部露白 */
#app.app--competition-detail,
#app.app--competition-detail .app-main {
  background-color: #0a0618;
}

.site-beian-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  padding: 8px 16px;
  text-align: center;
  line-height: 1.5;
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.site-beian-footer a {
  font-size: 12px;
  color: #666;
  text-decoration: none;
  margin: 0 8px;
}

.site-beian-footer a:hover {
  color: #1890ff;
}

/* 竞赛详情页：备案栏背景与详情一致，文字白色 */
.site-beian-footer--dark {
  background: #0a0618;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.site-beian-footer--dark a {
  color: #fff;
}

.site-beian-footer--dark a:hover {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: underline;
}
</style>
