import type { UserRoleCode } from '@/types/auth'

const ROLE_LABELS: Record<UserRoleCode, string> = {
  admin: '系统管理员',
  coach: '教练账号',
  training: '队伍训练端账号',
}

export function getUserRoleLabel(roleCode: UserRoleCode | string | null | undefined) {
  if (roleCode === 'admin' || roleCode === 'coach' || roleCode === 'training') {
    return ROLE_LABELS[roleCode]
  }
  return '未知角色'
}
