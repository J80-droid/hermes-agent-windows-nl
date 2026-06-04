import { useContext } from "react";
import { AssistantDisplayContext } from "./assistant-display-context";

export function useAssistantDisplay() {
  return useContext(AssistantDisplayContext);
}
