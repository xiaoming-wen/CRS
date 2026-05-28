<template>
  <div class="enrollments-registration-full">
    <div class="enrollments-registration-full-toolbar">
      <a-button type="link" class="back-btn" @click="goBack">
        <a-icon type="left" />
        返回竞赛报名系统
      </a-button>
    </div>
    <div class="enrollments-registration-full-body">
      <MyCompetitionEnrollments />
    </div>
  </div>
</template>

<script>
import MyCompetitionEnrollments from '@/views/manus/MyCompetitionEnrollments.vue'

export default {
  name: 'MyCompetitionEnrollmentsFullPage',
  components: { MyCompetitionEnrollments },
  methods: {
    goBack () {
      this.$router.push({ name: 'ManuVideo' }).catch(() => {})
    }
  }
}
</script>

<style scoped lang="less">
.enrollments-registration-full {
  min-height: 100vh;
  background: #f5f5f5;
}

.enrollments-registration-full-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  padding-left: 0;
  font-size: 14px;
}

.enrollments-registration-full-body {
  padding: 16px;
  max-width: 100%;
  box-sizing: border-box;
}
</style>
