export type AppMode = 'training' | 'management' | 'monitor'

export type UserRoleCode = 'admin' | 'coach' | 'training'

export type AuthUser = {
  id: number
  username: string
  display_name: string
  role_code: UserRoleCode
  team_id: number | null
  team_name: string | null
  mode: AppMode
  available_modes: AppMode[]
  can_manage_users: boolean
  can_manage_system: boolean
  can_switch_athletes: boolean
  is_active: boolean
}
