import client from './client'
import type { UserRoleCode } from '@/types/auth'

export type UserManagementRead = {
  id: number
  username: string
  display_name: string
  role_code: UserRoleCode
  sport_id: number | null
  sport_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type UserCreatePayload = {
  username: string
  display_name: string
  role_code: UserRoleCode
  sport_id: number | null
  is_active: boolean
  password: string
}

export type UserUpdatePayload = {
  display_name?: string
  role_code?: UserRoleCode
  sport_id?: number | null
  is_active?: boolean
}

export type UserPasswordResetPayload = {
  password: string
}

export async function fetchUsers(): Promise<UserManagementRead[]> {
  const { data } = await client.get('/users')
  return data
}

export async function createUser(payload: UserCreatePayload): Promise<UserManagementRead> {
  const { data } = await client.post('/users', payload)
  return data
}

export async function updateUser(userId: number, payload: UserUpdatePayload): Promise<UserManagementRead> {
  const { data } = await client.patch(`/users/${userId}`, payload)
  return data
}

export async function resetUserPassword(userId: number, payload: UserPasswordResetPayload): Promise<UserManagementRead> {
  const { data } = await client.post(`/users/${userId}/reset-password`, payload)
  return data
}

export async function deactivateUser(userId: number): Promise<UserManagementRead> {
  const { data } = await client.post(`/users/${userId}/deactivate`)
  return data
}

export async function activateUser(userId: number): Promise<UserManagementRead> {
  const { data } = await client.post(`/users/${userId}/activate`)
  return data
}
