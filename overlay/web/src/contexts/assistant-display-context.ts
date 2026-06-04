import { createContext } from "react";
import type { AssistantDisplaySettings } from "@/lib/api";

export const DEFAULT_ASSISTANT_DISPLAY: AssistantDisplaySettings = {
  assistant_render_style: "institutional_rich",
  assistant_palette: "demo",
  assistant_label_columns: true,
};

export type AssistantDisplayContextValue = AssistantDisplaySettings & {
  loading: boolean;
  refresh: () => Promise<void>;
};

export const AssistantDisplayContext = createContext<AssistantDisplayContextValue>({
  ...DEFAULT_ASSISTANT_DISPLAY,
  loading: true,
  refresh: async () => {},
});
