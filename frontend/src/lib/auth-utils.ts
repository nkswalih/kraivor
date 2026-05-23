export const setAuthCookie = () => {
  if (typeof document !== 'undefined') {
    // 30 days
    document.cookie = `kraivor_auth=true; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
  }
};

export const clearAuthCookie = () => {
  if (typeof document !== 'undefined') {
    document.cookie = "kraivor_auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
  }
};
