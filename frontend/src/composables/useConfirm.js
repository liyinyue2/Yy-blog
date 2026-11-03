/**
 * useConfirm —— 玻璃模态确认，替代浏览器原生 confirm()
 * 用法：if (!(await confirmAsk({ title: '删除文章', text: '不可恢复' }))) return
 */
import { reactive, readonly } from 'vue'

const state = reactive({
  open: false,
  title: '',
  text: '',
  detail: '',
  okLabel: '确定',
  cancelLabel: '取消',
  danger: true,
})

let settle = null

export const confirmState = readonly(state)

export function confirmAsk(options = {}) {
  const { title = '请确认', text = '', detail = '', ok = '确定', cancel = '取消', danger = true } = options
  Object.assign(state, { open: true, title, text, detail, okLabel: ok, cancelLabel: cancel, danger })
  return new Promise(resolve => { settle = resolve })
}

export function settleConfirm(value) {
  state.open = false
  settle?.(value)
  settle = null
}
