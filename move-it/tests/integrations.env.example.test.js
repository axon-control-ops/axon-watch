const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync, existsSync } = require("node:fs");
const { join } = require("node:path");

const ROOT = join(__dirname, "..");
const ENV_EXAMPLE = join(ROOT, "config", "env.example");

const REQUIRED_KEYS = [
  "GITHUB_TOKEN",
  "GH_TOKEN",
  "SENTRY_AUTH_TOKEN",
  "SENTRY_ORG",
  "SENTRY_PROJECT",
  "SENTRY_DSN",
  "SUPABASE_URL",
  "SUPABASE_SERVICE_ROLE_KEY",
  "SUPABASE_ANON_KEY",
  "SUPABASE_ACCESS_TOKEN",
];

test("config/env.example documents service-connection keys", () => {
  assert.ok(existsSync(ENV_EXAMPLE), "config/env.example must exist");

  const content = readFileSync(ENV_EXAMPLE, "utf8");
  for (const key of REQUIRED_KEYS) {
    assert.match(content, new RegExp(`^${key}=`, "m"), `missing placeholder ${key}=`);
  }

  assert.doesNotMatch(content, /=(sk_|ghp_|eyJ)/, "must not contain secret-like values");
});
