import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import { useShellStore } from './stores/shell';
import './styles/app.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const shell = useShellStore(pinia);
void shell.loadBootstrapData();

app.mount('#app');
