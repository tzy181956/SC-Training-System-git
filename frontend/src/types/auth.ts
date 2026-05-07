export type AppMode = 'training' | 'management' | 'monitor'

export type UserRoleCode = 'admin' | 'coach'

export type AuthUser = {
  id: number
  username: string
  display_name: string
  role_code: UserRoleCode
  sport_id: number | null
  sport_name: string | null
  mode: AppMode
  available_modes: AppMode[]
  can_manage_users: boolean
  can_manage_system: boolean
  is_active: boolean
}
