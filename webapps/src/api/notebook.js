import { axios } from '@/utils/request'

export function executeCode (parameter) {
  return axios({
    url: '/notebook/execute',
    method: 'post',
    data: parameter,
    timeout: 60000
  })
}

export function getEnvironments () {
  return axios({
    url: '/notebook/environments',
    method: 'get'
  })
}

export function stopExecution (executionId) {
  return axios({
    url: '/notebook/stop',
    method: 'post',
    data: { executionId }
  })
}
