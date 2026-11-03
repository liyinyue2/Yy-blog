/** 全站共享枚举与中文标签（此前在 4 个文件里各写一份且不一致） */

export const PROJECT_STATUS = {
  building: '开发中',
  maintained: '维护中',
  idea: '构想中',
  archived: '已归档',
}

export const projectStatusLabel = status => PROJECT_STATUS[status] || status || ''
