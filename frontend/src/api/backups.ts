import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export interface BackupItem {
  filename: string
  path: string
  stem: string
  restore_point_at: string
  file_modified_at: string
  size_bytes: number
  trigger: string | null
  trigger_label: string | null
  label: string | null
  naming_scheme: string
  is_managed: boolean
}

export interface RestoreScope {
  key: 'full_database' | 'training_records' | 'test_records'
  label: string
  description: string
  impact_summary: string[]
  affected_tables: string[]
}

export interface BackupListResponse {
  backup_directory: string
  filename_pattern: string
  keep_recent_days: number
  keep_recent_weeks: number
  items: BackupItem[]
  available_restore_scopes: RestoreScope[]
}

export interface BackupRestoreResponse {
  backup_filename: string
  backup_path: string
  restore_scope: string
  restore_scope_label: string
  restore_point_at: string
  team_id: number | null
  team_name: string | null
  restored_tables: string[]
  restored_row_counts: Record<string, { deleted: number; inserted: number }>
  pre_restore_backup_path: string | null
  message: string
}

export async function fetchBackups() {
  const { data } = await client.get<BackupListResponse>('/backups')
  return data
}

export async function restoreBackup(
  payload: DangerousActionPayload & {
    backup_filename: string
    restore_scope: 'full_database' | 'training_records' | 'test_records'
    team_id?: number | null
  },
) {
  const { data } = await client.post<BackupRestoreResponse>('/backups/restore', payload)
  return data
}
