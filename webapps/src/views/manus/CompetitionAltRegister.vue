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
                    <a-select-option value="teacher">教师</a-select-option>
                  </a-select>
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

                <a-form-item v-if="form.getFieldValue('role') === 'teacher'">
                  <a-input
                    size="large"
                    type="text"
                    placeholder="请输入教师编号"
                    v-decorator="[
                      'teacher_id',
                      { rules: [{ required: true, message: '请输入教师编号' }], validateTrigger: 'change' }
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
    handleRoleChange () {
      this.$nextTick(() => {
        const currentRole = this.form.getFieldValue('role')
        if (currentRole !== 'student') {
          this.form.setFieldsValue({ student_id: undefined })
        }
        if (currentRole !== 'teacher') {
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
      } else if (currentRole === 'teacher') {
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
          if (values.role === 'teacher') {
            registerParams.teacher_id = values.teacher_id
          }

          altIdentityRegister(registerParams)
            .then((res) => {
              if (res && (res.id != null || res.user_id != null || res.access_token)) {
                this.$message.success('注册成功！')
                setTimeout(() => {
                  this.$router.push({ name: 'ManuVideoCompetition' }).catch(() => {})
                }, 1500)
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
  }
}
</style>
