import { useEffect, useState } from 'react'
import { uiPreferences, PREF_CHANGE_EVENT } from '../utils/UIPreferences'

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
