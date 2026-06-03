import { create } from "zustand";
import type { SurveillanceEvent } from "../types";
import { listEvents, acknowledgeEvent as apiAck } from "../services/api";

interface EventFilters {
  severity?: string;
  event_type?: string;
  video_id?: string;
  acknowledged?: boolean;
  min_threat_score?: number;
  page: number;
  page_size: number;
}

interface EventsState {
  events: SurveillanceEvent[];
  total: number;
  filters: EventFilters;
  isLoading: boolean;
  liveEvents: SurveillanceEvent[];
  setFilter: (key: keyof EventFilters, value: unknown) => void;
  clearFilters: () => void;
  fetch: () => Promise<void>;
  acknowledge: (eventId: string, analystName: string) => Promise<void>;
  addLiveEvent: (event: SurveillanceEvent) => void;
}

const DEFAULT_FILTERS: EventFilters = { page: 1, page_size: 50 };

export const useEventsStore = create<EventsState>((set, get) => ({
  events: [],
  total: 0,
  filters: DEFAULT_FILTERS,
  isLoading: false,
  liveEvents: [],

  setFilter: (key, value) => {
    set((s) => ({ filters: { ...s.filters, [key]: value, page: 1 } }));
    get().fetch();
  },

  clearFilters: () => {
    set({ filters: DEFAULT_FILTERS });
    get().fetch();
  },

  fetch: async () => {
    set({ isLoading: true });
    try {
      const { filters } = get();
      const res = await listEvents(
        Object.fromEntries(
          Object.entries(filters).filter(([, v]) => v !== undefined && v !== "" && v !== null)
        )
      );
      set({ events: res.items, total: res.total, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  acknowledge: async (eventId, analystName) => {
    await apiAck(eventId, analystName);
    set((s) => ({
      events: s.events.map((e) =>
        e.event_id === eventId
          ? { ...e, acknowledged: true, acknowledged_by: analystName }
          : e
      ),
      liveEvents: s.liveEvents.map((e) =>
        e.event_id === eventId
          ? { ...e, acknowledged: true, acknowledged_by: analystName }
          : e
      ),
    }));
  },

  addLiveEvent: (event) => {
    set((s) => ({
      liveEvents: [event, ...s.liveEvents].slice(0, 100),
    }));
  },
}));
