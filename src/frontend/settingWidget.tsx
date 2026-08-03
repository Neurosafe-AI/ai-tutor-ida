/**
 * SURA Agent - Settings Widget
 * 
 * Provides the React UI for the expandable "Agent Setting" panel.
 * Handles state for user preferences like auto-assist toggles, error thresholds,
 * LLM model selection (local vs API), and persona roles.
 */
import * as React from 'react';
import { useState, useEffect } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { ReactWidget } from '@jupyterlab/apputils';
import {
  Button,
  InputGroup,
  settingsIcon,
  caretDownIcon,
  caretUpIcon,
  closeIcon,
  checkIcon
} from '@jupyterlab/ui-components';
import { getNudgeConfig, updateNudgeConfig, fetchAvailableModels } from './configAPI';

interface IAgentSettingsPanelProps {
  onClose?: () => void;
  initialExpanded?: boolean;
}

/**
 * React Component representing the floating Agent Settings panel.
 */
export const AgentSettingsExpandablePanel: React.FC<IAgentSettingsPanelProps> = ({
  onClose,
  initialExpanded = true
}) => {
  // UI State
  const [isExpanded, setIsExpanded] = useState<boolean>(initialExpanded);
  const [statusMessage, setStatusMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [saving, setSaving] = useState<boolean>(false);

  // Preference State
  const [enableNudge, setEnableNudge] = useState<boolean>(true);
  const [errorThreshold, setErrorThreshold] = useState<number>(3);
  const [llmModel, setLlmModel] = useState<string>('ollama/qwen2.5-coder:1.5b');
  const [customModel, setCustomModel] = useState<string>('');
  const [isCustomModel, setIsCustomModel] = useState<boolean>(false);
  const [apiKey, setApiKey] = useState<string>('');
  const [agentRole, setAgentRole] = useState<string>('systems_architect');
  const [availableModels, setAvailableModels] = useState<string[]>([]);

  // Fetch preferences from backend on mount
  useEffect(() => {
    getNudgeConfig()
      .then(cfg => {
        if (cfg && cfg.enable_inline_nudge !== undefined) {
          setEnableNudge(cfg.enable_inline_nudge);
        }
        if (cfg && cfg.error_threshold !== undefined) {
          setErrorThreshold(cfg.error_threshold);
        }
        if (cfg && cfg.llm_model) {
          const defaultModels = ['ollama/qwen2.5-coder:1.5b', 'gpt-4o', 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'];
          if (defaultModels.includes(cfg.llm_model)) {
            setLlmModel(cfg.llm_model);
            setIsCustomModel(false);
          } else {
            setLlmModel('custom');
            setCustomModel(cfg.llm_model);
            setIsCustomModel(true);
          }
        }
        if (cfg && cfg.api_key) {
          setApiKey(cfg.api_key);
        }
        if (cfg && cfg.agent_role) {
          setAgentRole(cfg.agent_role);
        }
      })
      .catch(err => {
        console.error('[SURA Agent] Error fetching config:', err);
        setStatusMessage({ text: 'Failed to fetch agent settings.', isError: true });
      });

    fetchAvailableModels()
      .then(models => {
        if (Array.isArray(models) && models.length > 0) {
          setAvailableModels(models);
        }
      })
      .catch(err => console.error('[SURA Agent] Error fetching available models:', err));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatusMessage(null);
    try {
      const finalModel = isCustomModel ? customModel : llmModel;
      await updateNudgeConfig({
        enable_inline_nudge: enableNudge,
        error_threshold: errorThreshold,
        llm_model: finalModel,
        api_key: apiKey,
        agent_role: agentRole
      });
      setStatusMessage({ text: 'Settings saved successfully!', isError: false });
    } catch (err) {
      console.error('[SURA Agent] Error saving config:', err);
      setStatusMessage({ text: 'Error saving settings.', isError: true });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`sura-agent-expand-panel ${isExpanded ? 'is-expanded' : 'is-collapsed'}`}>
      <div className="sura-expand-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="sura-expand-header-title">
          <settingsIcon.react tag="span" className="sura-header-icon" />
          <span>Agent Setting</span>
        </div>
        <div className="sura-expand-header-actions" onClick={e => e.stopPropagation()}>
          <button
            className="sura-icon-btn"
            title={isExpanded ? 'Collapse settings' : 'Expand settings'}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <caretUpIcon.react tag="span" />
            ) : (
              <caretDownIcon.react tag="span" />
            )}
          </button>
          {onClose && (
            <button className="sura-icon-btn" title="Close settings" onClick={onClose}>
              <closeIcon.react tag="span" />
            </button>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="sura-expand-body">
          <div className="jp-FormGroup sura-form-group">
            <div className="sura-switch-row">
              <span className="sura-label-text">Enable Inline Mentor Nudges (Auto-Assist)</span>
              <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  className="jp-mod-styled"
                  checked={enableNudge}
                  onChange={e => setEnableNudge(e.target.checked)}
                />
              </label>
            </div>
            <div className="jp-FormGroup-subForm sura-sub-form">
              Shows proactive emotional support notes below failing notebook execution cells.
            </div>
          </div>

          <div className="jp-FormGroup sura-form-group">
            <label className="sura-label-text">Consecutive Failure Threshold</label>
            <div style={{ width: '130px', marginTop: '6px' }}>
              <InputGroup
                type="number"
                value={String(errorThreshold)}
                onChange={e => setErrorThreshold(Number(e.target.value))}
                min={1}
                max={10}
              />
            </div>
            <div className="jp-FormGroup-subForm sura-sub-form">
              Number of consecutive cell errors required to trigger break suggestions.
            </div>
          </div>

          <div className="jp-FormGroup sura-form-group">
            <label className="sura-label-text">Agent Language Model</label>
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '13px', color: 'var(--jp-ui-font-color1)' }}>
                <input
                  type="radio"
                  name="model_type"
                  style={{ marginRight: '6px' }}
                  checked={!isCustomModel}
                  onChange={() => {
                    setIsCustomModel(false);
                    setLlmModel('ollama/qwen2.5-coder:1.5b');
                  }}
                />
                Default Local Model (qwen2.5-coder:1.5b)
              </label>
              
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '13px', color: 'var(--jp-ui-font-color1)' }}>
                <input
                  type="radio"
                  name="model_type"
                  style={{ marginRight: '6px' }}
                  checked={isCustomModel}
                  onChange={() => setIsCustomModel(true)}
                />
                Custom API Model
              </label>
            </div>

            {isCustomModel && (
              <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '16px', borderLeft: '2px solid var(--jp-border-color2)' }}>
                <div>
                  <label className="sura-label-text" style={{ fontSize: '12px' }}>Search Target Model</label>
                  <div style={{ marginTop: '4px' }}>
                    <input
                      type="text"
                      className="jp-mod-styled"
                      style={{ width: '100%', boxSizing: 'border-box' }}
                      placeholder="e.g. ollama/deepseek-coder or gpt-4o"
                      value={customModel}
                      onChange={e => setCustomModel(e.target.value)}
                      list="sura-llm-models-list"
                    />
                    <datalist id="sura-llm-models-list">
                      {availableModels.length > 0 ? (
                        availableModels.map(model => (
                          <option key={model} value={model} />
                        ))
                      ) : (
                        <>
                          <option value="gpt-4o" />
                          <option value="claude-3-5-sonnet-20241022" />
                          <option value="gemini-1.5-pro" />
                          <option value="ollama/deepseek-coder" />
                        </>
                      )}
                    </datalist>
                  </div>
                </div>
                <div>
                  <label className="sura-label-text" style={{ fontSize: '12px' }}>API Key (Optional for Local)</label>
                  <div style={{ marginTop: '4px' }}>
                    <InputGroup
                      type="password"
                      placeholder="sk-..."
                      value={apiKey}
                      onChange={e => setApiKey(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="jp-FormGroup sura-form-group">
            <label className="sura-label-text">Agent Persona Role</label>
            <div style={{ marginTop: '6px' }}>
              <select
                className="jp-mod-styled"
                style={{ width: '100%', padding: '4px', fontSize: '13px' }}
                value={agentRole}
                onChange={e => setAgentRole(e.target.value)}
              >
                <option value="systems_architect">Systems Architect (Default)</option>
                <option value="teaching_assistant">Teaching Assistant</option>
                <option value="empathetic_friend">Empathetic Friend</option>
                <option value="strict_instructor">Strict Instructor</option>
              </select>
            </div>
            <div className="jp-FormGroup-subForm sura-sub-form">
              Customize the agent's tone, goal, and interaction style.
            </div>
          </div>

          <div className="sura-expand-footer">
            <Button
              className="jp-mod-styled jp-mod-accept"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </Button>

            {statusMessage && (
              <span
                className={`sura-status-msg ${statusMessage.isError ? 'is-error' : 'is-success'}`}
              >
                {!statusMessage.isError && (
                  <span style={{ marginRight: '4px', display: 'inline-flex', alignItems: 'center' }}>
                    <checkIcon.react tag="span" />
                  </span>
                )}
                {statusMessage.text}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

let settingsContainer: HTMLElement | null = null;
let settingsRoot: Root | null = null;
let isPanelVisible = false;

export function toggleAgentSettingsExpandable(): void {
  if (isPanelVisible && settingsContainer) {
    if (settingsRoot) {
      try {
        settingsRoot.unmount();
      } catch (_) {}
      settingsRoot = null;
    }
    if (settingsContainer.parentNode) {
      settingsContainer.parentNode.removeChild(settingsContainer);
    }
    settingsContainer = null;
    isPanelVisible = false;
    return;
  }

  const existing = document.getElementById('sura-agent-expand-setting-root');
  if (existing && existing.parentNode) {
    existing.parentNode.removeChild(existing);
  }

  settingsContainer = document.createElement('div');
  settingsContainer.id = 'sura-agent-expand-setting-root';
  document.body.appendChild(settingsContainer);

  const panelElement = React.createElement(AgentSettingsExpandablePanel, {
    initialExpanded: true,
    onClose: () => {
      toggleAgentSettingsExpandable();
    }
  });

  try {
    settingsRoot = createRoot(settingsContainer);
    settingsRoot.render(panelElement);
    isPanelVisible = true;
    console.log('[SURA Agent] Settings panel opened via createRoot.');
    return;
  } catch (err) {
    console.warn('[SURA Agent] createRoot failed, attempting legacy ReactDOM.render fallback:', err);
  }

  try {
    const ReactDOM = require('react-dom');
    if (ReactDOM && typeof ReactDOM.render === 'function') {
      ReactDOM.render(panelElement, settingsContainer);
      isPanelVisible = true;
      console.log('[SURA Agent] Settings panel opened via legacy ReactDOM.render.');
      return;
    }
  } catch (err2) {
    console.error('[SURA Agent] Legacy ReactDOM.render also failed:', err2);
  }

  if (settingsContainer) {
    settingsContainer.innerHTML = `
      <div style="
        position: fixed; top: 42px; right: 20px; z-index: 999999;
        background: #fff; border: 2px solid #d32f2f; border-radius: 8px;
        padding: 16px 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.18);
        font-family: var(--jp-ui-font-family, sans-serif); max-width: 340px;
      ">
        <strong style="color: #d32f2f;">⚠ Settings Panel Error</strong>
        <p style="margin: 8px 0 0; font-size: 13px; color: #424242;">
          Could not render the Agent Settings panel. Try reloading JupyterLab.
        </p>
      </div>
    `;
    isPanelVisible = true;
  }
}

export class AgentSettingsWidget extends ReactWidget {
  constructor() {
    super();
    this.addClass('jp-AgentSettingsWidget');
  }

  render(): JSX.Element {
    return <AgentSettingsExpandablePanel />;
  }
}
