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
          <a-form
            id="formCompetitionAltRegister"
            class="user-layout-register"
            :form="form"
            @submit="handleSubmit"
          >
            <a-tabs :tabBarStyle="{ textAlign: 'center', borderBottom: 'unset' }">
              <a-tab-pane key="tab1" tab="用户注册">
                <a-form-item>
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入用户名"
                    v-decorator="[
                      'username',
                      {
                        rules: [
                          { required: true, message: '请输入用户名' },
                          { min: 3, message: '用户名至少3个字符' },
                          { max: 100, message: '用户名最长100个字符' }
                        ],
                        validateTrigger: 'change'
                      }
                    ]"
                    @focus="hintFocus.username = true"
                    @blur="hintFocus.username = false"
                  >
                    <a-icon slot="prefix" type="user" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                  <template slot="extra">
                    <span
                      v-show="hintFocus.username"
                      class="register-field-hint"
                    >至少 3 个字符，最长 100 个字符；建议使用字母、数字或下划线。</span>
                  </template>
                </a-form-item>

                <a-form-item>
                  <a-input
                    size="large"
                    type="email"
                    placeholder="请输入邮箱"
                    v-decorator="[
                      'email',
                      { rules: [{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入正确的邮箱地址' }], validateTrigger: 'change' }
                    ]"
                  >
                    <a-icon slot="prefix" type="mail" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                </a-form-item>

                <a-form-item>
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入姓名"
                    v-decorator="[
                      'full_name',
                      { rules: [{ required: true, message: '请输入姓名' }], validateTrigger: 'change' }
                    ]"
                  >
                    <a-icon slot="prefix" type="idcard" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                </a-form-item>

                <a-form-item>
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入学校名称"
                    v-decorator="[
                      'school',
                      {
                        rules: [
                          { required: true, message: '请输入学校名称' },
                          { max: 200, message: '学校名称最长200个字符' }
                        ],
                        validateTrigger: 'change'
                      }
                    ]"
                    @focus="hintFocus.school = true"
                    @blur="hintFocus.school = false"
                  >
                    <a-icon slot="prefix" type="bank" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                </a-form-item>

                <a-form-item>
                  <a-select
                    size="large"
                    placeholder="请选择角色"
                    v-decorator="[
                      'role',
                      { rules: [{ required: true, message: '请选择角色' }], validateTrigger: 'change' }
                    ]"
                    @change="handleRoleChange"
                  >
                    <a-select-option value="student">学生</a-select-option>
                    <a-select-option value="advisor">指导老师</a-select-option>
                    <a-select-option value="expert">专家</a-select-option>
                    <a-select-option value="school_admin">校管理员</a-select-option>
                  </a-select>
                  <template slot="extra">
                    <span
                      v-if="form.getFieldValue('role') === 'expert'"
                      class="register-field-hint register-field-hint--info"
                    >专家可在此自助注册，注册成功后 <code>expert_verified</code> 为 <strong>false</strong>，<strong>暂不可登录</strong>。请牢记系统提示的<strong>用户 ID</strong>，待管理员核验（§8.0.6）并指派竞赛（§8.0.7）后再登录评阅。</span>
                    <span
                      v-else-if="form.getFieldValue('role') === 'school_admin'"
                      class="register-field-hint register-field-hint--info"
                    >校管理员可在此自助注册，注册成功后可正常登录。登录后须提交资料（含照片）并经超级管理员审核通过后，方可进行本校组队校审。</span>
                  </template>
                </a-form-item>

                <a-form-item v-if="form.getFieldValue('role') === 'student'">
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入学号"
                    v-decorator="[
                      'student_id',
                      { rules: [{ required: true, message: '请输入学号' }], validateTrigger: 'change' }
                    ]"
                  >
                    <a-icon slot="prefix" type="number" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                </a-form-item>

                <a-form-item v-if="form.getFieldValue('role') === 'advisor'">
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入指导老师编号"
                    v-decorator="[
                      'teacher_id',
                      { rules: [{ required: true, message: '请输入指导老师编号' }], validateTrigger: 'change' }
                    ]"
                  >
                    <a-icon slot="prefix" type="number" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input>
                </a-form-item>

                <a-form-item>
                  <a-input-password
                    size="large"
                    autocomplete="false"
                    placeholder="请输入密码"
                    v-decorator="[
                      'password',
                      { rules: [{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }], validateTrigger: 'blur' }
                    ]"
                    @focus="hintFocus.password = true"
                    @blur="hintFocus.password = false"
                  >
                    <a-icon slot="prefix" type="lock" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input-password>
                  <template slot="extra">
                    <span
                      v-show="hintFocus.password"
                      class="register-field-hint"
                    >至少 6 个字符，建议包含字母与数字。</span>
                  </template>
                </a-form-item>

                <a-form-item>
                  <a-input-password
                    size="large"
                    autocomplete="false"
                    placeholder="请再次输入密码"
                    v-decorator="[
                      'confirmPassword',
                      { rules: [{ required: true, message: '请确认密码' }, { validator: compareToFirstPassword }], validateTrigger: 'blur' }
                    ]"
                    @focus="hintFocus.confirmPassword = true"
                    @blur="hintFocus.confirmPassword = false"
                  >
                    <a-icon slot="prefix" type="lock" :style="{ color: 'rgba(0,0,0,.25)' }" />
                  </a-input-password>
                  <template slot="extra">
                    <span
                      v-show="hintFocus.confirmPassword"
                      class="register-field-hint"
                    >请与上方密码保持一致。</span>
                  </template>
                </a-form-item>
              </a-tab-pane>
            </a-tabs>

            <a-form-item style="margin-top: 24px">
              <a-button
                size="large"
                type="primary"
                htmlType="submit"
                class="register-button"
                :loading="state.registerBtn"
                :disabled="state.registerBtn"
              >注册</a-button>
            </a-form-item>

            <a-form-item>
              <router-link
                :to="{ name: 'ManuVideoCompetition' }"
                class="login-link"
                style="text-align: center; display: block;"
              >已有账号？去登录</router-link>
            </a-form-item>
          </a-form>
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
import { altIdentityRegister } from '@/api/altIdentity'
import { showRegisterConflictModal, extractRegisterError } from '@/utils/registerConflict'

export default {
  name: 'CompetitionAltRegister',
  mixins: [mixinDevice],
  data () {
    return {
      hintFocus: {
        username: false,
        school: false,
        password: false,
        confirmPassword: false
      },
      form: this.$form.createForm(this),
      state: {
        registerBtn: false
      }
    }
  },
  mounted () {
    document.body.classList.add('userLayout')
  },
  beforeDestroy () {
    document.body.classList.remove('userLayout')
  },
  methods: {
    isAdvisorRegisterRole (role) {
      return role === 'advisor' || role === 'teacher'
    },
    handleRoleChange () {
      this.$nextTick(() => {
        const currentRole = this.form.getFieldValue('role')
        if (currentRole !== 'student') {
          this.form.setFieldsValue({ student_id: undefined })
        }
        if (!this.isAdvisorRegisterRole(currentRole)) {
          this.form.setFieldsValue({ teacher_id: undefined })
        }
      })
    },
    compareToFirstPassword (rule, value, callback) {
      const form = this.form
      if (value && value !== form.getFieldValue('password')) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    },
    handleSubmit (e) {
      e.preventDefault()
      const {
        form: { validateFields },
        state
      } = this

      state.registerBtn = true

      const validateFieldsKey = ['username', 'email', 'full_name', 'school', 'role', 'password', 'confirmPassword']
      const currentRole = this.form.getFieldValue('role')
      if (currentRole === 'student') {
        validateFieldsKey.push('student_id')
      } else if (this.isAdvisorRegisterRole(currentRole)) {
        validateFieldsKey.push('teacher_id')
      }

      validateFields(validateFieldsKey, { force: true }, (err, values) => {
        if (!err) {
          const registerParams = {
            username: values.username,
            email: values.email,
            full_name: values.full_name,
            school: (values.school || '').trim(),
            password: values.password,
            role: values.role
          }
          if (values.role === 'student') {
            registerParams.student_id = values.student_id
          }
          if (this.isAdvisorRegisterRole(values.role)) {
            registerParams.role = 'advisor'
            registerParams.teacher_id = values.teacher_id
          }

          altIdentityRegister(registerParams)
            .then((res) => {
              if (res && (res.id != null || res.user_id != null || res.access_token)) {
                const registeredId = res.id != null ? res.id : res.user_id
                if (values.role === 'expert' && registeredId != null) {
                  this.$notification.success({
                    message: '专家注册成功',
                    description: `您的用户 ID 为 ${registeredId}。当前待管理员核验，暂无法登录。请将 ID 告知管理员，在「专家指派」中完成核验与竞赛指派后再登录。`,
                    duration: 0
                  })
                  setTimeout(() => {
                    this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
                  }, 6000)
                } else if (values.role === 'school_admin') {
                  this.$notification.success({
                    message: '校管理员注册成功',
                    description: '您可立即登录。登录后请提交资料申请（含照片），待超级管理员审核通过后方可进行本校组队校审。',
                    duration: 6
                  })
                  setTimeout(() => {
                    this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
                  }, 2000)
                } else {
                  this.$message.success('注册成功！')
                  setTimeout(() => {
                    this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
                  }, 1500)
                }
              } else {
                this.$message.error('注册失败，请重试')
              }
            })
            .catch(err => {
              if (!showRegisterConflictModal(this, err)) {
                this.requestFailed(err)
              }
            })
            .finally(() => {
              state.registerBtn = false
            })
        } else {
          setTimeout(() => {
            state.registerBtn = false
          }, 600)
        }
      })
    },
    requestFailed (err) {
      const desc = extractRegisterError(err) || '请求出现错误，请稍后再试'
      this.$notification.error({
        message: '注册失败',
        description: desc,
        duration: 4
      })
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

.user-layout-register {
  label {
    font-size: 14px;
  }

  button.register-button {
    padding: 0 15px;
    font-size: 16px;
    height: 40px;
    width: 100%;
  }

  .login-link {
    color: #1890ff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .register-field-hint {
    display: block;
    color: #f5222d;
    font-size: 14px;
    line-height: 1.5;

    &--info {
      color: rgba(0, 0, 0, 0.45);
    }
  }
}
</style>
