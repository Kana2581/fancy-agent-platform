import React, { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Braces,
  Plus,
  Save,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type {
  StructuredOutputField,
  StructuredOutputFieldType,
  StructuredOutputSchemaInput,
  StructuredOutputSchemaOut,
} from '../api'
import { StructuredOutputSchemasService } from '../api'

type FormField = Omit<StructuredOutputField, 'item_fields'> & {
  __uid: string
  item_fields?: FormField[] | null
}

type StructuredOutputForm = Omit<StructuredOutputSchemaInput, 'field_config'> & {
  field_config: {
    fields: FormField[]
  }
}

const FIELD_TYPES: { value: StructuredOutputFieldType; label: string }[] = [
  { value: 'string', label: '文本' },
  { value: 'number', label: '数字' },
  { value: 'integer', label: '整数' },
  { value: 'boolean', label: '布尔值' },
  { value: 'date', label: '日期' },
  { value: 'enum', label: '枚举' },
  { value: 'object_array', label: '对象列表' },
]

const ITEM_FIELD_TYPES = FIELD_TYPES.filter((type) => type.value !== 'object_array')

const createUid = () => crypto.randomUUID()

const emptyField = (): FormField => ({
  __uid: createUid(),
  key: '',
  label: '',
  type: 'string',
  description: '',
  enum_values: null,
  item_fields: null,
})

const emptyItemField = (): FormField => emptyField()

const emptyForm = (): StructuredOutputForm => ({
  name: '',
  description: '',
  field_config: { fields: [emptyField()] },
})

const cloneField = (field: StructuredOutputField): FormField => ({
  __uid: createUid(),
  ...field,
  enum_values: field.enum_values ? [...field.enum_values] : null,
  item_fields: field.item_fields ? field.item_fields.map(cloneField) : null,
})

const normalizeFieldForSave = (field: FormField): StructuredOutputField => {
  const { __uid: _uid, ...rest } = field
  return {
    ...rest,
    key: rest.key.trim(),
    label: rest.label.trim(),
    description: rest.description?.trim() || null,
    enum_values:
      rest.type === 'enum'
        ? (rest.enum_values ?? []).map((value) => value.trim()).filter(Boolean)
        : null,
    item_fields:
      rest.type === 'object_array'
        ? (rest.item_fields ?? []).map(normalizeFieldForSave)
        : null,
  }
}

const StructuredOutputSchemasPage: React.FC = () => {
  const navigate = useNavigate()
  const [schemas, setSchemas] = useState<StructuredOutputSchemaOut[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [form, setForm] = useState<StructuredOutputForm>(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const selected = useMemo(
    () => schemas.find((schema) => schema.id === selectedId) ?? null,
    [schemas, selectedId]
  )

  useEffect(() => {
    StructuredOutputSchemasService.list()
      .then(setSchemas)
      .catch((error) => {
        console.error(error)
        toast.error('加载 Schema 失败')
      })
      .finally(() => setLoading(false))
  }, [])

  const selectSchema = (schema: StructuredOutputSchemaOut) => {
    setSelectedId(schema.id)
    setForm({
      name: schema.name,
      description: schema.description ?? '',
      field_config: {
        fields: schema.field_config.fields.map(cloneField),
      },
    })
  }

  const createNew = () => {
    setSelectedId(null)
    setForm(emptyForm())
  }

  const updateField = (index: number, patch: Partial<FormField>) => {
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.map((field, fieldIndex) =>
          fieldIndex === index ? { ...field, ...patch } : field
        ),
      },
    }))
  }

  const updateItemField = (fieldIndex: number, itemIndex: number, patch: Partial<FormField>) => {
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.map((field, index) => {
          if (index !== fieldIndex) return field
          const itemFields = field.item_fields ?? []
          return {
            ...field,
            item_fields: itemFields.map((item, childIndex) =>
              childIndex === itemIndex ? { ...item, ...patch } : item
            ),
          }
        }),
      },
    }))
  }

  const addItemField = (fieldIndex: number) => {
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.map((field, index) =>
          index === fieldIndex
            ? { ...field, item_fields: [...(field.item_fields ?? []), emptyItemField()] }
            : field
        ),
      },
    }))
  }

  const moveItemField = (fieldIndex: number, itemIndex: number, offset: -1 | 1) => {
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.map((field, index) => {
          if (index !== fieldIndex) return field
          const itemFields = [...(field.item_fields ?? [])]
          const target = itemIndex + offset
          if (target < 0 || target >= itemFields.length) return field
          ;[itemFields[itemIndex], itemFields[target]] = [itemFields[target], itemFields[itemIndex]]
          return { ...field, item_fields: itemFields }
        }),
      },
    }))
  }

  const removeItemField = (fieldIndex: number, itemIndex: number) => {
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.map((field, index) => {
          if (index !== fieldIndex) return field
          const itemFields = field.item_fields ?? []
          if (itemFields.length === 1) return field
          return {
            ...field,
            item_fields: itemFields.filter((_, childIndex) => childIndex !== itemIndex),
          }
        }),
      },
    }))
  }

  const moveField = (index: number, offset: -1 | 1) => {
    const target = index + offset
    if (target < 0 || target >= form.field_config.fields.length) return
    setForm((current) => {
      const fields = [...current.field_config.fields]
      ;[fields[index], fields[target]] = [fields[target], fields[index]]
      return { ...current, field_config: { fields } }
    })
  }

  const removeField = (index: number) => {
    if (form.field_config.fields.length === 1) return
    setForm((current) => ({
      ...current,
      field_config: {
        fields: current.field_config.fields.filter((_, fieldIndex) => fieldIndex !== index),
      },
    }))
  }

  const validate = (): string | null => {
    if (!form.name.trim()) return '请输入 Schema 名称'
    const validateFields = (fields: StructuredOutputField[], prefix: string): string | null => {
      const keys = fields.map((field) => field.key.trim())
      if (fields.some((field) => !field.key.trim() || !field.label.trim())) {
        return `${prefix}字段 key 和显示名称不能为空`
      }
      if (keys.some((key) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(key))) {
        return `${prefix}字段 key 只能使用英文字母、数字和下划线，且不能以数字开头`
      }
      if (new Set(keys).size !== keys.length) return `${prefix}字段 key 不能重复`
      if (
        fields.some((field) => field.type === 'enum' && !(field.enum_values?.filter(Boolean).length))
      ) {
        return `${prefix}枚举字段至少需要一个枚举值`
      }
      for (const field of fields) {
        if (field.type !== 'object_array') continue
        if (!(field.item_fields?.length)) return `对象列表「${field.label || field.key}」至少需要一个子字段`
        const childError = validateFields(field.item_fields, `对象列表「${field.label || field.key}」的`)
        if (childError) return childError
      }
      return null
    }
    return validateFields(form.field_config.fields, '')
  }

  const save = async () => {
    const error = validate()
    if (error) {
      toast.error(error)
      return
    }
    const payload: StructuredOutputSchemaInput = {
      name: form.name.trim(),
      description: form.description?.trim() || null,
      field_config: {
        fields: form.field_config.fields.map(normalizeFieldForSave),
      },
    }
    setSaving(true)
    try {
      const result = selected
        ? await StructuredOutputSchemasService.update(selected.id, payload)
        : await StructuredOutputSchemasService.create(payload)
      setSchemas((current) =>
        selected
          ? current.map((schema) => (schema.id === result.id ? result : schema))
          : [result, ...current]
      )
      selectSchema(result)
      toast.success('Schema 已保存')
    } catch (error) {
      console.error(error)
      toast.error('保存 Schema 失败')
    } finally {
      setSaving(false)
    }
  }

  const deleteSelected = async () => {
    if (!selected || !confirm(`确定删除「${selected.name}」吗？`)) return
    try {
      await StructuredOutputSchemasService.delete(selected.id)
      setSchemas((current) => current.filter((schema) => schema.id !== selected.id))
      createNew()
    } catch (error) {
      console.error(error)
      toast.error('删除 Schema 失败')
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50 dark:bg-zinc-950 text-gray-900 dark:text-gray-100">
      <header className="border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => navigate('/chat')}
              title="返回聊天"
              className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-800"
            >
              <ArrowLeft size={18} />
            </button>
            <Braces size={22} />
            <h1 className="text-xl font-semibold truncate">结构化输出</h1>
          </div>
          <button
            type="button"
            onClick={createNew}
            className="px-4 py-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 flex items-center gap-2"
          >
            <Plus size={17} />
            新建 Schema
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-[15rem_minmax(0,1fr)] gap-6">
        <aside className="lg:border-r lg:border-gray-200 dark:lg:border-zinc-800 lg:pr-5">
          <div className="text-xs font-medium text-gray-500 mb-2">SCHEMAS</div>
          {loading ? (
            <div className="text-sm text-gray-500 py-4">加载中...</div>
          ) : (
            <div className="space-y-1">
              {schemas.map((schema) => (
                <button
                  type="button"
                  key={schema.id}
                  onClick={() => selectSchema(schema)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm truncate ${
                    selectedId === schema.id
                      ? 'bg-gray-200 dark:bg-zinc-800 font-medium'
                      : 'hover:bg-gray-100 dark:hover:bg-zinc-900'
                  }`}
                >
                  {schema.name}
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="min-w-0 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium block mb-1">名称</span>
              <input
                value={form.name}
                maxLength={100}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 outline-none focus:ring-2 focus:ring-cyan-500/30"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium block mb-1">说明</span>
              <input
                value={form.description ?? ''}
                maxLength={1000}
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 outline-none focus:ring-2 focus:ring-cyan-500/30"
              />
            </label>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">字段</h2>
              <button
                type="button"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    field_config: {
                      fields: [...current.field_config.fields, emptyField()],
                    },
                  }))
                }
                className="px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 flex items-center gap-2 text-sm hover:bg-gray-100 dark:hover:bg-zinc-800"
              >
                <Plus size={16} />
                添加字段
              </button>
            </div>

            <div className="space-y-3">
              {form.field_config.fields.map((field, index) => (
                <div
                  key={field.__uid}
                  className="border border-gray-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900 p-4"
                >
                  <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_10rem_auto] gap-3 items-end">
                    <label>
                      <span className="text-xs text-gray-500 block mb-1">Key</span>
                      <input
                        value={field.key}
                        maxLength={64}
                        onChange={(event) => updateField(index, { key: event.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent font-mono text-sm"
                      />
                    </label>
                    <label>
                      <span className="text-xs text-gray-500 block mb-1">显示名称</span>
                      <input
                        value={field.label}
                        maxLength={100}
                        onChange={(event) => updateField(index, { label: event.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm"
                      />
                    </label>
                    <label>
                      <span className="text-xs text-gray-500 block mb-1">类型</span>
                      <select
                        value={field.type}
                        onChange={(event) => {
                          const nextType = event.target.value as StructuredOutputFieldType
                          updateField(index, {
                            type: nextType,
                            enum_values: nextType === 'enum' ? [''] : null,
                            item_fields: nextType === 'object_array' ? [emptyItemField()] : null,
                          })
                        }}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm"
                      >
                        {FIELD_TYPES.map((type) => (
                          <option key={type.value} value={type.value}>
                            {type.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="flex gap-1">
                      <button type="button" title="上移" onClick={() => moveField(index, -1)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30" disabled={index === 0}><ArrowUp size={15} /></button>
                      <button type="button" title="下移" onClick={() => moveField(index, 1)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30" disabled={index === form.field_config.fields.length - 1}><ArrowDown size={15} /></button>
                      <button type="button" title="删除字段" onClick={() => removeField(index)} className="w-8 h-8 flex items-center justify-center rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-30" disabled={form.field_config.fields.length === 1}><Trash2 size={15} /></button>
                    </div>
                  </div>
                  <label className="block mt-3">
                    <span className="text-xs text-gray-500 block mb-1">字段描述</span>
                    <input
                      value={field.description ?? ''}
                      maxLength={500}
                      onChange={(event) => updateField(index, { description: event.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm"
                    />
                  </label>
                  {field.type === 'enum' && (
                    <label className="block mt-3">
                      <span className="text-xs text-gray-500 block mb-1">枚举值（每行一个）</span>
                      <textarea
                        value={(field.enum_values ?? []).join('\n')}
                        onChange={(event) =>
                          updateField(index, { enum_values: event.target.value.split('\n') })
                        }
                        rows={3}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm resize-y"
                      />
                    </label>
                  )}
                  {field.type === 'object_array' && (
                    <div className="mt-4 rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 p-3">
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <div className="text-xs font-medium text-gray-500">列表项子字段</div>
                        <button
                          type="button"
                          onClick={() => addItemField(index)}
                          className="px-2.5 py-1.5 rounded-lg border border-gray-300 dark:border-zinc-700 flex items-center gap-1.5 text-xs hover:bg-gray-100 dark:hover:bg-zinc-800"
                        >
                          <Plus size={14} />
                          添加子字段
                        </button>
                      </div>
                      <div className="space-y-2">
                        {(field.item_fields ?? []).map((itemField, itemIndex) => (
                          <div
                            key={itemField.__uid}
                            className="grid grid-cols-1 md:grid-cols-[1fr_1fr_9rem_auto] gap-2 items-end"
                          >
                            <label>
                              <span className="text-xs text-gray-500 block mb-1">Key</span>
                              <input
                                value={itemField.key}
                                maxLength={64}
                                onChange={(event) =>
                                  updateItemField(index, itemIndex, { key: event.target.value })
                                }
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent font-mono text-sm"
                              />
                            </label>
                            <label>
                              <span className="text-xs text-gray-500 block mb-1">显示名称</span>
                              <input
                                value={itemField.label}
                                maxLength={100}
                                onChange={(event) =>
                                  updateItemField(index, itemIndex, { label: event.target.value })
                                }
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm"
                              />
                            </label>
                            <label>
                              <span className="text-xs text-gray-500 block mb-1">类型</span>
                              <select
                                value={itemField.type}
                                onChange={(event) => {
                                  const nextType = event.target.value as StructuredOutputFieldType
                                  updateItemField(index, itemIndex, {
                                    type: nextType,
                                    enum_values: nextType === 'enum' ? [''] : null,
                                    item_fields: null,
                                  })
                                }}
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm"
                              >
                                {ITEM_FIELD_TYPES.map((type) => (
                                  <option key={type.value} value={type.value}>
                                    {type.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <div className="flex gap-1">
                              <button type="button" title="上移" onClick={() => moveItemField(index, itemIndex, -1)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30" disabled={itemIndex === 0}><ArrowUp size={15} /></button>
                              <button type="button" title="下移" onClick={() => moveItemField(index, itemIndex, 1)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30" disabled={itemIndex === (field.item_fields?.length ?? 0) - 1}><ArrowDown size={15} /></button>
                              <button type="button" title="删除子字段" onClick={() => removeItemField(index, itemIndex)} className="w-8 h-8 flex items-center justify-center rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-30" disabled={(field.item_fields?.length ?? 0) === 1}><Trash2 size={15} /></button>
                            </div>
                            <label className="md:col-span-4">
                              <span className="text-xs text-gray-500 block mb-1">字段描述</span>
                              <input
                                value={itemField.description ?? ''}
                                maxLength={500}
                                onChange={(event) =>
                                  updateItemField(index, itemIndex, { description: event.target.value })
                                }
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm"
                              />
                            </label>
                            {itemField.type === 'enum' && (
                              <label className="md:col-span-4">
                                <span className="text-xs text-gray-500 block mb-1">枚举值（每行一个）</span>
                                <textarea
                                  value={(itemField.enum_values ?? []).join('\n')}
                                  onChange={(event) =>
                                    updateItemField(index, itemIndex, {
                                      enum_values: event.target.value.split('\n'),
                                    })
                                  }
                                  rows={3}
                                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-sm resize-y"
                                />
                              </label>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-between border-t border-gray-200 dark:border-zinc-800 pt-5">
            <button
              type="button"
              onClick={() => void deleteSelected()}
              disabled={!selected}
              className="px-4 py-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-30 flex items-center gap-2"
            >
              <Trash2 size={17} />
              删除
            </button>
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="px-5 py-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-50 flex items-center gap-2"
            >
              <Save size={17} />
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </section>
      </main>
    </div>
  )
}

export default StructuredOutputSchemasPage
