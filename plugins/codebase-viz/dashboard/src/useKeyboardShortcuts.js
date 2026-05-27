import React from 'react';

/** Tabs mapped to keys 1–9 and 0 (plan §8.3). */
export const SHORTCUT_TABS = [
  'sunburst',
  'force-graph',
  'treemap',
  'metrics',
  'churn',
  'age-map',
  'complexity',
  'todos',
  'blame',
  'coverage',
];

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

/**
 * @param {{ setTab: (id: string) => void, onRefresh: () => void }} opts
 */
export function useKeyboardShortcuts({ setTab, onRefresh }) {
  React.useEffect(() => {
    const handler = (e) => {
      if (isTypingTarget(e.target)) return;

      if (e.key >= '1' && e.key <= '9') {
        const tab = SHORTCUT_TABS[parseInt(e.key, 10) - 1];
        if (tab) {
          e.preventDefault();
          setTab(tab);
        }
        return;
      }
      if (e.key === '0') {
        e.preventDefault();
        setTab('coverage');
        return;
      }
      if (e.key === 'Escape') {
        window.dispatchEvent(new CustomEvent('codebase-viz:escape'));
        return;
      }
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        onRefresh();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setTab, onRefresh]);
}
