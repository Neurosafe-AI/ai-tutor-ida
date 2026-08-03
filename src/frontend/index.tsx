/**
 * SURA Agent - Frontend Entry Point
 * 
 * This file registers the core JupyterLab UI extensions:
 * 1. Notebook Toolbar Toggle: Adds the "Auto-Assist" switch.
 * 2. Kernel Injector: Secretly installs the Python error watcher into running notebooks.
 * 3. Top Menu: Registers the "Agent Setting" menu and command palette actions.
 */
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { DocumentRegistry } from '@jupyterlab/docregistry';
import { Switch, settingsIcon } from '@jupyterlab/ui-components';
import { ICommandPalette } from '@jupyterlab/apputils';
import { IMainMenu } from '@jupyterlab/mainmenu';
import { Menu, Widget } from '@lumino/widgets';

import { fetchMentorConfig, setMentorConfig } from './configAPI';
import { toggleAgentSettingsExpandable } from './settingWidget';
import { setupChatboxQuickActionObserver } from './quickActions';

import '../../style/index.css';

/**
 * Extension that adds the "Auto-Assist" toggle switch to every notebook's toolbar.
 */
export class MentorToolbarExtension
  implements DocumentRegistry.IWidgetExtension<NotebookPanel, any> {
  createNew(panel: NotebookPanel): any {
    const toggle = new Switch();

    toggle.addClass('sura-mentor-switch');
    toggle.label = 'Auto-Assist';
    toggle.caption = 'Toggle in-line emotional support messages';

    let isApplyingConfig = false;
    let currentValue = true;

    toggle.valueChanged.connect(async (sender, args) => {
      if (isApplyingConfig) {
        return;
      }

      const nextValue = args.newValue;
      const saved = await setMentorConfig(nextValue);

      if (saved) {
        currentValue = nextValue;
      } else {
        isApplyingConfig = true;
        sender.value = currentValue;
        isApplyingConfig = false;
        console.error('[SURA Agent] Failed to save mentor toggle state.');
        // Disable switch visually if there's an error so the user knows it's broken
        toggle.node.style.pointerEvents = 'none';
        toggle.node.style.opacity = '0.5';
        toggle.caption = 'Error: Connection to backend lost.';
      }
    });

    fetchMentorConfig().then(cfg => {
      if (cfg && cfg.enable_inline_nudge !== undefined) {
        currentValue = cfg.enable_inline_nudge;
      }
      isApplyingConfig = true;
      toggle.value = currentValue;
      isApplyingConfig = false;
    }).catch(() => {
      toggle.node.style.pointerEvents = 'none';
      toggle.node.style.opacity = '0.5';
      toggle.caption = 'Error: Connection to backend lost.';
    });

    panel.toolbar.insertItem(10, 'suraMentorToggle', toggle);
    return toggle;
  }
}

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'sura-agent:mentor-toggle',
  autoStart: true,
  requires: [],
  optional: [INotebookTracker, ICommandPalette, IMainMenu],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker | null,
    palette: ICommandPalette | null,
    mainMenu: IMainMenu | null
  ) => {
    console.log('SURA Agent Frontend Extension activated!');

    setupChatboxQuickActionObserver();

    if (tracker) {
      app.docRegistry.addWidgetExtension('Notebook', new MentorToolbarExtension());

      tracker.widgetAdded.connect((sender, panel) => {
        const sessionContext = panel.sessionContext;
        sessionContext.kernelChanged.connect(async () => {
          try {
            await sessionContext.ready;
            const kernel = sessionContext.session?.kernel;
            if (!kernel) return;

            const code = `
try:
    from sura_agent.error_watcher import setup_watcher
    setup_watcher()
except Exception as e:
    import sys
    print(f"Error loading sura_agent error watcher: {e}", file=sys.stderr)
`;
            kernel.requestExecute({ code, silent: true, store_history: false });
          } catch (err) {
            console.error('[SURA Agent] Failed to inject kernel error watcher:', err);
          }
        });
      });
    }

    const command = 'sura-agent:open-settings';

    app.commands.addCommand(command, {
      label: 'Preferences...',
      caption: 'Toggle SURA Agent Settings Expandable Panel',
      icon: settingsIcon,
      execute: () => {
        toggleAgentSettingsExpandable();
      }
    });

    if (palette) {
      palette.addItem({ command, category: 'SURA Agent' });
    }

    if (mainMenu) {
      const agentMenu = new Menu({ commands: app.commands });
      agentMenu.title.label = 'Agent Setting';
      agentMenu.addItem({ command });

      mainMenu.addMenu(agentMenu, true, { rank: 800 });
    }
  }
};

export default plugin;
