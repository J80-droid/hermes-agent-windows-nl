/**
 * Maps `import ... from 'react'` to the Hermes Plugin SDK (browser IIFE build).
 * Do not bundle the npm `react` package — it is not available at runtime.
 */
function getSDK() {
  const SDK = typeof window !== 'undefined' ? window.__HERMES_PLUGIN_SDK__ : null;
  if (!SDK?.React) {
    throw new Error('Hermes Plugin SDK React is not available');
  }
  if (!SDK.hooks?.useEffect || !SDK.hooks?.useRef) {
    throw new Error('Hermes Plugin SDK hooks are not available');
  }
  return SDK;
}

const SDK = getSDK();
const React = SDK.React;

export default React;
export const useEffect = SDK.hooks.useEffect;
export const useRef = SDK.hooks.useRef;
