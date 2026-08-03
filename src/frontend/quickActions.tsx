/**
 * SURA Agent - Quick Actions UI
 * 
 * This module is responsible for injecting the "Debug", "Explain", and "Take Break" 
 * buttons directly into the JupyterLab Chat UI. Because the chat UI might be rendered 
 * dynamically, this uses a MutationObserver to watch the DOM and insert buttons 
 * into the chat input toolbar when it appears.
 */
import * as React from 'react';
import { createRoot } from 'react-dom/client';
import {
  Button,
  bugIcon,
  codeIcon,
  pauseIcon
} from '@jupyterlab/ui-components';

interface IQuickActionProps {
  onAction?: (actionText: string) => void;
}

export const QUICK_ACTION_PROMPTS = {
  debug: '@LocalAI Please inspect my active notebook and working files, discover potential errors or failing code, and help me debug them.',
  explain: '@LocalAI Please inspect my active notebook and working files, and explain the code structure, key functions, and overall logic.',
  takeBreak: '@LocalAI I am taking a brief break from coding right now.'
};

export function sendPromptText(text: string): void {
  // Find textarea inside the chat input container (handles jupyterlab-chat v0.22.x lowercase classes)
  let targetInput: HTMLTextAreaElement | HTMLInputElement | HTMLElement | null = null;
  let targetContainer: Element | null = null;

  const chatContainers = document.querySelectorAll('.jp-chat-input-container');

  for (let i = 0; i < chatContainers.length; i++) {
    const container = chatContainers[i];
    const input = container.querySelector('textarea, input[type="text"], [contenteditable="true"]');
    if (input) {
      targetInput = input as any;
      targetContainer = container;
      break;
    }
  }

  // Fallback broad search
  if (!targetInput) {
    const fallbackSelectors = [
      '.jp-chat-widget textarea',
      '[class*="chat-input"] textarea',
      '[class*="chat"] textarea',
      '.jp-Chat-input textarea',
      'textarea[placeholder*="chat"]'
    ];
    for (const sel of fallbackSelectors) {
      const el = document.querySelector(sel);
      if (el) {
        targetInput = el as any;
        targetContainer = el.closest('.jp-chat-input-container, .jp-chat-widget, [class*="chat"], .jp-Chat-input');
        break;
      }
    }
  }

  if (!targetInput) {
    console.warn('[SURA Agent] Chat input element not found in DOM.');
    return;
  }

  // Populate input text
  if (targetInput instanceof HTMLTextAreaElement || targetInput instanceof HTMLInputElement) {
    const nativeSetter =
      Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set ||
      Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;

    if (nativeSetter) {
      nativeSetter.call(targetInput, text);
    } else {
      targetInput.value = text;
    }
    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
    targetInput.dispatchEvent(new Event('change', { bubbles: true }));
  } else if (targetInput.isContentEditable) {
    targetInput.textContent = text;
    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  // Trigger send after a short delay
  setTimeout(() => {
    const sendBtn =
      (targetContainer && targetContainer.querySelector('.jp-chat-send-button, button[class*="send"], button[class*="Send"]')) ||
      document.querySelector('.jp-chat-send-button') ||
      document.querySelector('button[title*="Send"], button[aria-label*="Send"]');

    if (sendBtn) {
      (sendBtn as HTMLButtonElement).click();
      return;
    }

    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true
    });
    targetInput?.dispatchEvent(enterEvent);
  }, 60);
}

export const QuickActionButtons: React.FC<IQuickActionProps> = ({ onAction }) => {
  const handleAction = (promptText: string) => {
    if (onAction) {
      onAction(promptText);
    } else {
      sendPromptText(promptText);
    }
  };

  return (
    <div className="sura-quick-actions-container">
      <button
        className="sura-quick-action-btn"
        onClick={() => handleAction(QUICK_ACTION_PROMPTS.debug)}
        title="Debug: Inspect working file & discover potential errors"
      >
        <span>Debug</span>
      </button>
      <button
        className="sura-quick-action-btn"
        onClick={() => handleAction(QUICK_ACTION_PROMPTS.explain)}
        title="Explain: Explain code structure & logic in working file"
      >
        <span>Explain</span>
      </button>
      <button
        className="sura-quick-action-btn"
        onClick={() => handleAction(QUICK_ACTION_PROMPTS.takeBreak)}
        title="Take Break: Request emotional support & brief breather"
      >
        <span>Take Break</span>
      </button>
    </div>
  );
};

export function findAndInjectChatQuickActions(): void {
  // Target the actual toolbar classes (jupyterlab-chat and jupyter-ai)
  const toolbars = document.querySelectorAll('.jp-chat-input-toolbar, .jp-Chat-input-controls, .jp-Chat-toolbar, [class*="chat-input"] [class*="toolbar"]');
  toolbars.forEach(toolbar => {
    if (!toolbar.querySelector('.sura-quick-actions-mount')) {
      injectIntoContainer(toolbar as HTMLElement);
    }
  });

  // Fallback target container
  if (document.querySelectorAll('.sura-quick-actions-mount').length === 0) {
    const containers = document.querySelectorAll('.jp-chat-input-container, .jp-Chat-input, .jp-Chat-input-area, .jp-ai-Chat-input');
    containers.forEach(container => {
      if (!container.querySelector('.sura-quick-actions-mount')) {
        // Find a div that contains a button, avoiding :has() which causes DOMException
        let toolbar: HTMLElement | null = null;
        const potentialToolbars = container.querySelectorAll('.jp-chat-input-toolbar, .jp-Chat-toolbar, div');
        for (let i = 0; i < potentialToolbars.length; i++) {
          const el = potentialToolbars[i] as HTMLElement;
          if (el.matches('.jp-chat-input-toolbar, .jp-Chat-toolbar') || el.querySelector('button')) {
            toolbar = el;
            break;
          }
        }
        
        if (toolbar && !toolbar.querySelector('.sura-quick-actions-mount')) {
          injectIntoContainer(toolbar);
        } else if (!container.querySelector('.sura-quick-actions-mount')) {
          injectIntoContainer(container as HTMLElement);
        }
      }
    });
  }
}

function injectIntoContainer(container: HTMLElement): void {
  if (container.querySelector('.sura-quick-actions-mount')) {
    return;
  }

  // Flex fix if needed
  const computedStyle = window.getComputedStyle(container);
  if (computedStyle.display !== 'flex') {
    container.style.display = 'flex';
  }
  container.style.flexDirection = 'row';
  container.style.alignItems = 'center';

  const mountPoint = document.createElement('div');
  mountPoint.className = 'sura-quick-actions-mount';

  if (container.firstChild) {
    container.insertBefore(mountPoint, container.firstChild);
  } else {
    container.appendChild(mountPoint);
  }

  try {
    const root = createRoot(mountPoint);
    root.render(<QuickActionButtons />);
  } catch (e) {
    console.error('[SURA Agent] Error mounting QuickActionButtons:', e);
  }
}

let chatObserver: MutationObserver | null = null;
let isQuickReplyListenerAttached = false;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export function setupChatboxQuickActionObserver(): void {
  findAndInjectChatQuickActions();

  if (!isQuickReplyListenerAttached) {
    document.addEventListener('click', (event: MouseEvent) => {
      const target = (event.target as HTMLElement).closest('.sura-quick-reply-btn');
      if (target) {
        event.preventDefault();
        event.stopPropagation();
        const promptText = target.getAttribute('data-prompt') || target.getAttribute('title') || target.textContent || '';
        if (promptText) {
          let agentPrefix = '';
          const match = target.className.match(/sura-persona-([^\s]+)/);
          if (match && match[1]) {
            agentPrefix = `@${match[1]} `;
          }
          sendPromptText(agentPrefix + promptText.trim());
        }
      }
    });
    isQuickReplyListenerAttached = true;
  }

  if (!chatObserver) {
    chatObserver = new MutationObserver(() => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
      debounceTimer = setTimeout(() => {
        findAndInjectChatQuickActions();
      }, 200);
    });
    chatObserver.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
}
