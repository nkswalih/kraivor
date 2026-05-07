import { useUIStore } from '@/lib/stores';

export function useUI() {
  const { sidebarOpen, sidebarCollapsed, theme, toasts, toggleSidebar, setSidebarOpen, toggleSidebarCollapse, setTheme, addToast, removeToast } = useUIStore();

  return {
    sidebarOpen,
    sidebarCollapsed,
    theme,
    toasts,
    toggleSidebar,
    setSidebarOpen,
    toggleSidebarCollapse,
    setTheme,
    addToast,
    removeToast,
  };
}