/**
 * Example dashboard plugin — minimal IIFE (no build step).
 * Keeps /api/plugins/example/ test coverage; avoids 404 on dist/index.js.
 */
(function () {
  'use strict';

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK?.React || !window.__HERMES_PLUGINS__?.register) return;

  const h = SDK.React.createElement;

  function ExampleApp() {
    return h(
      'div',
      { className: 'example-plugin-panel', style: { padding: '1rem' } },
      h('h3', { style: { margin: '0 0 0.5rem', fontSize: '1rem' } }, 'Example plugin'),
      h(
        'p',
        { style: { margin: 0, fontSize: '0.85rem', color: 'hsl(var(--muted-foreground))' } },
        'Demo-tab voor plugin-API-tests. Backend: ',
        h('code', null, 'GET /api/plugins/example/hello'),
      ),
    );
  }

  window.__HERMES_PLUGINS__.register('example', ExampleApp);
})();
