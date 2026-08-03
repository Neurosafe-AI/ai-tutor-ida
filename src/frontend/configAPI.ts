/**
 * SURA Agent - Configuration API Client
 * 
 * This module handles all network requests between the JupyterLab frontend
 * and the Jupyter Server Python backend endpoints. It fetches and persists
 * user settings stored in ~/.duck_events/config.json.
 */
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection } from '@jupyterlab/services';

export interface IAgentConfig {
  enable_inline_nudge: boolean;
  error_threshold?: number;
  llm_model?: string;
  api_key?: string;
  agent_role?: string;
  [key: string]: any;
}

/**
 * Fetches current agent configuration state from backend endpoint
 */
export async function fetchMentorConfig(): Promise<IAgentConfig> {
  const settings = ServerConnection.makeSettings();
  let requestUrl = URLExt.join(settings.baseUrl, 'duck_events', 'config');

  try {
    let response = await ServerConnection.makeRequest(requestUrl, {}, settings);
    if (!response.ok) {
      requestUrl = URLExt.join(settings.baseUrl, 'sura-agent', 'config');
      response = await ServerConnection.makeRequest(requestUrl, {}, settings);
    }
    if (!response.ok) {
      return { enable_inline_nudge: true, error_threshold: 3 };
    }
    return await response.json();
  } catch {
    return { enable_inline_nudge: true, error_threshold: 3 };
  }
}

/**
 * Alias for fetchMentorConfig for compatibility across components
 */
export const getNudgeConfig = fetchMentorConfig;

/**
 * Persists updated mentor toggle state specifically
 */
export async function setMentorConfig(enable: boolean): Promise<boolean> {
  const settings = ServerConnection.makeSettings();
  let requestUrl = URLExt.join(settings.baseUrl, 'duck_events', 'config');

  try {
    let response = await ServerConnection.makeRequest(
      requestUrl,
      {
        method: 'POST',
        body: JSON.stringify({ enable_inline_nudge: enable }),
      },
      settings
    );
    if (!response.ok) {
      requestUrl = URLExt.join(settings.baseUrl, 'sura-agent', 'config');
      response = await ServerConnection.makeRequest(
        requestUrl,
        {
          method: 'POST',
          body: JSON.stringify({ enable_inline_nudge: enable }),
        },
        settings
      );
    }
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Persists updated agent configuration state via backend POST
 */
export async function updateNudgeConfig(config: Partial<IAgentConfig>): Promise<any> {
  const settings = ServerConnection.makeSettings();
  let requestUrl = URLExt.join(settings.baseUrl, 'duck_events', 'config');

  let response = await ServerConnection.makeRequest(
    requestUrl,
    {
      method: 'POST',
      body: JSON.stringify(config),
    },
    settings
  );

  if (!response.ok) {
    requestUrl = URLExt.join(settings.baseUrl, 'sura-agent', 'config');
    response = await ServerConnection.makeRequest(
      requestUrl,
      {
        method: 'POST',
        body: JSON.stringify(config),
      },
      settings
    );
  }

  if (!response.ok) {
    throw new ServerConnection.ResponseError(response);
  }
  return await response.json();
}

/**
 * Fetches the exhaustive list of models from the backend.
 */
export async function fetchAvailableModels(): Promise<string[]> {
  const settings = ServerConnection.makeSettings();
  const requestUrl = URLExt.join(settings.baseUrl, 'duck_events', 'models');

  try {
    const response = await ServerConnection.makeRequest(requestUrl, {}, settings);
    if (!response.ok) {
      return [];
    }
    return await response.json();
  } catch {
    return [];
  }
}
