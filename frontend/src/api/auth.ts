import client from './client'
import type { AuthUser } from '@/types/auth'

export type TokenResponse = {
  access_token: string
  token_type: 'bearer'
}

export type VerifyPasswordResponse = {
  verified: true
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/login', { username, password })
  return data
}

export async function me(): Promise<AuthUser> {
  const { data } = await client.get<AuthUser>('/auth/me')
  return data
}

export async function verifyPassword(password: string): Promise<VerifyPasswordResponse> {
  const { data } = await client.post<VerifyPasswordResponse>('/auth/verify-password', { password })
  return data
}
