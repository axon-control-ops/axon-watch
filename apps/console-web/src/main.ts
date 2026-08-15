import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import { installKairoAudioUnlockListeners } from './lib/kairo-audio-unlock';
import { detectDesktopCapabilities } from './lib/desktop-capability';
import { useShellStore } from './stores/shell';
import './styles/app.css';

const desktopCaps = detectDesktopCapabilities();
document.documentElement.dataset.axonRuntime = desktopCaps.runtime;
document.documentElement.dataset.axonHostBridge = desktopCaps.hostBridge ? '1' : '0';
installKairoAudioUnlockListeners();

const app = createApp(App);
const pinia = createPinia();

// Without this, an uncaught error in a component's setup()/render/watcher had
// no safety net — Vue's default behavior for setup-phase errors can leave
// that subtree unmounted with nothing on screen and nothing in the console
// pointing at why. Log with enough context to find it, and keep the rest of
// the shell running instead of taking the whole page down with it.
app.config.errorHandler = (error, instance, info) => {
  const componentName = instance?.$options?.name ?? instance?.$.type?.__name ?? 'unknown component';
  console.error(`[axon-watch] uncaught error in ${componentName} (${info}):`, error);
};

// Fire-and-forget calls (`void someAsyncFn()`) that throw become unhandled
// promise rejections — the browser default is a console warning that's easy
// to miss and gives no indication anything is now stuck (e.g. a loading flag
// that never resets because the throw happened before its finally block).
window.addEventListener('unhandledrejection', (event) => {
  console.error('[axon-watch] unhandled promise rejection:', event.reason);
});

app.use(pinia);

const shell = useShellStore(pinia);
void shell.loadBootstrapData();

app.mount('#app');
