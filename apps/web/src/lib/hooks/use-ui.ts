import { useShallow } from 'zustand/shallow';
import { useUIStore } from '@/lib/stores';

export function useUI() {
  const sidebarOpen = useUIStore(s => s.sidebarOpen);
  const sidebarCollapsed = useUIStore(s => s.sidebarCollapsed);
  const theme = useUIStore(s => s.theme);
  const toggleSidebar = useUIStore(s => s.toggleSidebar);
  const setSidebarOpen = useUIStore(s => s.setSidebarOpen);
  const toggleSidebarCollapse = useUIStore(s => s.toggleSidebarCollapse);
  const setTheme = useUIStore(s => s.setTheme);
  const addToast = useUIStore(s => s.addToast);
  const removeToast = useUIStore(s => s.removeToast);
  const toasts = useUIStore(useShallow(s => s.toasts));

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
