import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, type AssistantDisplaySettings } from "@/lib/api";
import { ASSISTANT_DISPLAY_CHANGED } from "@/lib/assistantDisplayEvents";
import {
  AssistantDisplayContext,
  DEFAULT_ASSISTANT_DISPLAY,
} from "./assistant-display-context";

export function AssistantDisplayProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AssistantDisplaySettings>(
    DEFAULT_ASSISTANT_DISPLAY,
  );
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const next = await api.getAssistantDisplay();
      setSettings(next);
    } catch {
      /* keep last known settings */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void refresh();
    });
    const onChanged = () => {
      void refresh();
    };
    window.addEventListener(ASSISTANT_DISPLAY_CHANGED, onChanged);
    return () => window.removeEventListener(ASSISTANT_DISPLAY_CHANGED, onChanged);
  }, [refresh]);

  return (
    <AssistantDisplayContext.Provider value={{ ...settings, loading, refresh }}>
      {children}
    </AssistantDisplayContext.Provider>
  );
}
