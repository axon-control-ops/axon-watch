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

app.use(pinia);

const shell = useShellStore(pinia);
void shell.loadBootstrapData();

app.mount('#app');
