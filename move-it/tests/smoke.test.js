const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

test("MoveIT workspace smoke baseline is wired", () => {
  const manifestPath = join(__dirname, "..", "package.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  assert.equal(manifest.name, "move-it");
  assert.equal(typeof manifest.scripts?.test, "string");
});
