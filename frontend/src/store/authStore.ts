import { create } from "zustand";
import type { UserInfo } from "../types";
import { login as apiLogin, getMe } from "../services/api";
import { alertWS, requestNotificationPermission } from "../services/websocket";

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await apiLogin(username, password);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      const user = await getMe();
      alertWS.connect(tokens.access_token);
      await requestNotificationPermission();
      set({ user, token: tokens.access_token, isLoading: false, error: null });
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || "Login failed", isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    alertWS.disconnect();
    set({ user: null, token: null });
  },

  initialize: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    try {
      const user = await getMe();
      alertWS.connect(token);
      set({ user, token });
    } catch {
      localStorage.removeItem("access_token");
      set({ user: null, token: null });
    }
  },
}));
