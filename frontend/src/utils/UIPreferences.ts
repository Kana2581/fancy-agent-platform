export const HIDE_INTERMEDIATE_KEY = 'ui-hide-intermediate-messages'
export const PREF_CHANGE_EVENT = 'ui-pref-change'

export const uiPreferences = {
  getHideIntermediate(): boolean {
    return localStorage.getItem(HIDE_INTERMEDIATE_KEY) === 'true'
  },

  setHideIntermediate(value: boolean): void {
    localStorage.setItem(HIDE_INTERMEDIATE_KEY, value ? 'true' : 'false')
    window.dispatchEvent(new CustomEvent(PREF_CHANGE_EVENT))
  },
}
