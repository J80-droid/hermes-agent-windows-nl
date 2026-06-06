/** Fork dashboard API: toolset configure drawer (Tier B overlay). */
import { fetchJSON } from "@/lib/api";
import type { ActionResponse } from "@/lib/api";

export interface ToolsetProviderEnvVar {
  key: string;
  prompt: string;
  url: string | null;
  default: string | null;
  is_set: boolean;
}

export interface ToolsetProvider {
  name: string;
  badge: string;
  tag: string;
  env_vars: ToolsetProviderEnvVar[];
  post_setup: string | null;
  requires_nous_auth: boolean;
  is_active: boolean;
}

export interface ToolsetConfig {
  name: string;
  has_category: boolean;
  providers: ToolsetProvider[];
  active_provider: string | null;
}

export interface ToolsetEnvResult {
  ok: boolean;
  name: string;
  saved: string[];
  skipped: string[];
  is_set: Record<string, boolean>;
}

export const toolsetDashboardApi = {
  toggleToolset: (name: string, enabled: boolean) =>
    fetchJSON<{ ok: boolean; name: string; enabled: boolean }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
  getToolsetConfig: (name: string) =>
    fetchJSON<ToolsetConfig>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/config`,
    ),
  selectToolsetProvider: (name: string, provider: string) =>
    fetchJSON<{ ok: boolean; name: string; provider: string }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/provider`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider }),
      },
    ),
  saveToolsetEnv: (name: string, env: Record<string, string>) =>
    fetchJSON<ToolsetEnvResult>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/env`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ env }),
      },
    ),
  runToolsetPostSetup: (name: string, key: string) =>
    fetchJSON<ActionResponse & { key: string }>(
      `/api/tools/toolsets/${encodeURIComponent(name)}/post-setup`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      },
    ),
};
