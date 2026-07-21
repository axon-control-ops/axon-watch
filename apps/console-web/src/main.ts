import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import { useShellStore } from './stores/shell';
import './styles/app.css';

const debugRunId = `page-${Date.now().toString(36)}`;
const navigationEntry = performance.getEntriesByType('navigation')[0] as
  | PerformanceNavigationTiming
  | undefined;
// #region agent log
fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:debugRunId,hypothesisId:'H1',location:'main.ts:app-boot',message:'console application booted',data:{href:location.href,navigationType:navigationEntry?.type ?? 'unknown',visibility:document.visibilityState,timeOrigin:performance.timeOrigin},timestamp:Date.now()})}).catch(()=>{});
// #endregion
window.addEventListener('error', (event) => {
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:debugRunId,hypothesisId:'H5',location:'main.ts:window-error',message:'window error observed',data:{message:event.message,filename:event.filename,line:event.lineno,column:event.colno},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
});

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const shell = useShellStore(pinia);
void shell.loadBootstrapData();

app.mount('#app');
