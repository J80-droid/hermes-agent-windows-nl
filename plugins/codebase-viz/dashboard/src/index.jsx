import App from './App';

(function () {
  'use strict';
  if (!window.__HERMES_PLUGIN_SDK__) return;
  if (
    window.__HERMES_PLUGINS__ &&
    typeof window.__HERMES_PLUGINS__.register === 'function'
  ) {
    window.__HERMES_PLUGINS__.register('codebase-viz', App);
  }
})();
