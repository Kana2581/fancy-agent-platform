/* manually added — backend route is GET /api/v1/workspace/{session_id}/files */
/* tslint:disable */

export type WorkspaceFileOut = {
  file_id: number
  name: string
  ext: string
  size: number
  object_key: string
  session_id: string
}
