<template>
  <div class="not-found">
    <h1>404</h1>
    <p>页面不存在</p>
    <router-link to="/manu/competition-list">返回竞赛报名首页</router-link>
  </div>
</template>

<script>
export default {
  name: 'Exception404'
}
</script>

<style scoped>
.not-found {
  padding: 80px 24px;
  text-align: center;
}
</style>
