import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';

export type RightPanelView = 'ai' | 'activity' | 'details' | null;

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  description?: string;
  duration?: number;
}

interface UIState {
  // Sidebar State
  sidebarOpen: boolean; // For mobile slide-over
  sidebarCollapsed: boolean; // For desktop thin sidebar
  
  // Right Panel State (AI / Details)
  isRightPanelOpen: boolean;
  rightPanelView: RightPanelView;
  rightPanelContextId: string | null; // e.g., the ID of the repo you are asking AI about
  
  // Command Palette (Cmd+K)
  isCommandPaletteOpen: boolean;

  // Global UI
  theme: Theme;
  toasts: Toast[];
}

interface UIActions {
  // Sidebar Actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapse: () => void;
  
  // Right Panel Actions
  openRightPanel: (view?: RightPanelView, contextId?: string | null) => void;
  closeRightPanel: () => void;
  toggleRightPanel: () => void;
  
  // Command Palette Actions
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  // Global Actions
  setTheme: (theme: Theme) => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

type UIStore = UIState & UIActions;

export const useUIStore = create<UIStore>((set, get) => ({
  // ─── INITIAL STATE ──────────────────────────────────────────────────
  sidebarOpen: false,
  sidebarCollapsed: false,
  
  isRightPanelOpen: false,
  rightPanelView: null,
  rightPanelContextId: null,
  
  isCommandPaletteOpen: false,
  
  theme: 'system',
  toasts: [],

  // ─── ACTIONS ────────────────────────────────────────────────────────

  // Sidebar
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebarCollapse: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  // Right Panel
  openRightPanel: (view = 'ai', contextId = null) => set({ 
    isRightPanelOpen: true, 
    rightPanelView: view,
    rightPanelContextId: contextId 
  }),
  closeRightPanel: () => set({ 
    isRightPanelOpen: false,
    // We intentionally don't clear the view/context so it animates out nicely
  }),
  toggleRightPanel: () => set((state) => ({ 
    isRightPanelOpen: !state.isRightPanelOpen,
    // Default to AI view if opening via toggle
    rightPanelView: !state.isRightPanelOpen ? 'ai' : state.rightPanelView 
  })),

  // Command Palette
  setCommandPaletteOpen: (open) => set({ isCommandPaletteOpen: open }),
  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),

  // Theme
  setTheme: (theme) => set({ theme }),

  // Toasts
  addToast: (toast) =>
    set((state) => ({
      toasts: [
        ...state.toasts,
        { ...toast, id: Math.random().toString(36).substring(2, 9) },
      ],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export default useUIStore;