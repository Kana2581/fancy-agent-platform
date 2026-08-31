export type StructuredOutputFieldType =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'date'
  | 'enum'
  | 'object_array'

export type StructuredOutputField = {
  key: string
  label: string
  type: StructuredOutputFieldType
  description?: string | null
  enum_values?: string[] | null
  item_fields?: StructuredOutputField[] | null
}

export type StructuredOutputFieldConfig = {
  fields: StructuredOutputField[]
}

export type StructuredOutputSchemaInput = {
  name: string
  description?: string | null
  field_config: StructuredOutputFieldConfig
}

export type StructuredOutputSchemaOut = StructuredOutputSchemaInput & {
  id: number
  user_id: number
  created_at: string
  updated_at: string
}

export type StructuredOutputArtifact = {
  type: 'structured_output'
  schema_id: number
  schema_name?: string
  schema_snapshot: StructuredOutputFieldConfig
  data: Record<string, unknown>
  status: 'valid'
}
