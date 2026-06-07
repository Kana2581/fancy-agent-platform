const TOKEN_KEY = 'auth_token';

export const tokenManager = {
  getToken(): string {
    return localStorage.getItem(TOKEN_KEY) ?? '';
  },

  setToken(token: string | null | undefined): void {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      return;
    }
    localStorage.removeItem(TOKEN_KEY);
  },

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  },

  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem(TOKEN_KEY));
  },
};
