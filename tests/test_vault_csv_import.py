from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.vault.csv_import import (  # noqa: E402
    monitor_secrets_from_axon_rows,
    parse_axon_vault_csv,
    parse_vault_export_text,
)


class VaultCsvImportTests(unittest.TestCase):
    SAMPLE = """name,category,username,password,url,notes
SENTRY_AUTH_TOKEN,key,,sntry-token-value,https://edudash-pro.sentry.io/,
DASHPRO_SENTRY_ORG_SLUG,general,edudash-pro,edudash-pro,,
DASHPRO_POSTHOG_PROJECT_ID,general,,214649,,
POSTHOG_PERSONAL_API_KEY,key,,phx_test_key,https://us.posthog.com/,
EXPO_PUBLIC_POSTHOG_KEY,key,user@example.com,phc_test_key,https://us.posthog.com/,
Anthropic,key,,sk-should-not-import,https://platform.claude.com/,
"""

    def test_parse_axon_vault_csv_extracts_password_column(self) -> None:
        rows = parse_axon_vault_csv(self.SAMPLE)
        sentry = next(row for row in rows if row["name"] == "SENTRY_AUTH_TOKEN")
        self.assertEqual("sntry-token-value", sentry["password"])

    def test_monitor_secrets_map_aliases_and_filter_allowed_keys(self) -> None:
        rows = parse_axon_vault_csv(self.SAMPLE)
        secrets = monitor_secrets_from_axon_rows(rows)
        self.assertEqual("sntry-token-value", secrets["SENTRY_AUTH_TOKEN"])
        self.assertEqual("edudash-pro", secrets["SENTRY_ORG_SLUG"])
        self.assertEqual("214649", secrets["DASHPRO_POSTHOG_PROJECT_ID"])
        self.assertNotIn("Anthropic", secrets)
        self.assertNotIn("sk-should-not-import", secrets.values())

    def test_parse_vault_export_text_does_not_join_entire_csv_row_as_value(self) -> None:
        secrets = parse_vault_export_text(self.SAMPLE, filename="vault.csv")
        self.assertEqual("sntry-token-value", secrets["SENTRY_AUTH_TOKEN"])
        self.assertFalse(any("," in value for value in secrets.values()))


if __name__ == "__main__":
    unittest.main()
