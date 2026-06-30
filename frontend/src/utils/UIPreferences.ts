import { useEffect, useState } from 'react'

const HIDE_INTERMEDIATE_KEY = 'ui-hide-intermediate-messages'
const PREF_CHANGE_EVENT = 'ui-pref-change'

export const uiPreferences = {
  getHideIntermediate(): boolean {
    return localStorage.getItem(HIDE_INTERMEDIATE_KEY) === 'true'
  },

  setHideIntermediate(value: boolean): void {
    localStorage.setItem(HIDE_INTERMEDIATE_KEY, value ? 'true' : 'false')
    window.dispatchEvent(new CustomEvent(PREF_CHANGE_EVENT))
  },
}

export function useHideIntermediatePref(): [boolean, (value: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => uiPreferences.getHideIntermediate())

  useEffect(() => {
    const sync = () => setValue(uiPreferences.getHideIntermediate())
    window.addEventListener(PREF_CHANGE_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(PREF_CHANGE_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const update = (next: boolean) => {
    uiPreferences.setHideIntermediate(next)
    setValue(next)
  }

  return [value, update]
}
