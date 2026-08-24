import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { run } = require("vue-tsc");

const here = dirname(fileURLToPath(import.meta.url));
const tscPath = resolve(here, "../node_modules/typescript/lib/tsc.js");

process.argv = [process.argv[0], tscPath, ...process.argv.slice(2)];
run(tscPath);
