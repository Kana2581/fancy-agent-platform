import React, { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'

export interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

interface ThemedSelectProps {
  value: string | number
  onChange: (value: string) => void
  options: SelectOption[]
  className?: string
  disabled?: boolean
  required?: boolean
  placeholder?: string
}

const ThemedSelect: React.FC<ThemedSelectProps> = ({
  value,
  onChange,
  options,
  className = '',
  disabled = false,
  placeholder,
}) => {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = options.find((o) => String(o.value) === String(value))
  const displayLabel = selected ? selected.label : (placeholder ?? '')

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((v) => !v)}
        className={`${className} flex items-center justify-between gap-2 w-full text-left ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span className="truncate">{displayLabel}</span>
        <ChevronDown
          size={16}
          className={`shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-900/95 border border-gray-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-md">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={opt.disabled}
              onClick={() => {
                if (!opt.disabled) {
                  onChange(String(opt.value))
                  setOpen(false)
                }
              }}
              className={`w-full text-left px-4 py-2.5 text-sm text-gray-800 dark:text-white transition-colors
                ${String(opt.value) === String(value) ? 'bg-cyan-500/20 dark:bg-cyan-500/30' : 'hover:bg-gray-100 dark:hover:bg-zinc-700'}
                ${opt.disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ThemedSelect
