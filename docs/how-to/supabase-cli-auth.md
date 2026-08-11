# Supabase CLI auth for migration audits

DashPro migration audits need the Supabase CLI to compare local migration
history with the linked remote project. The safe, read-only unblock is:

```bash
cd /run/media/vaxon/axon-data/projectx/product/dashpro
node_modules/.bin/supabase migration list --linked
```

If this fails with `Access token not provided`, agents must self-heal in this
order:

1. Check `/vault` → **Supabase CLI migration checks**.
2. If the consumer is ready, retry through the normal Axon agent command path so
   the control-plane injects `SUPABASE_ACCESS_TOKEN` from Vault.
3. If it is missing, report the exact missing secret name
   (`SUPABASE_ACCESS_TOKEN`), the project ref, and the read-only command above.
   Never ask the operator to paste the token into chat.
4. Do **not** run `supabase db push` unless the migration comparison confirms
   pending files and the operator separately approves database deployment.

