/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

export type GeneratedImageOut = {
  id: number
  user_id: number
  image_tool_id?: number | null
  provider: string
  model_name: string
  prompt: string
  revised_prompt?: string | null
  object_key: string
  width?: number | null
  height?: number | null
  is_img2img: boolean
  created_at: string
  readonly image_url: string
  readonly thumbnail_url: string
}
