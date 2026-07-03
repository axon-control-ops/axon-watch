# Ops Skeleton

This directory is reserved for Lane 1 operational bootstrap helpers.

Current scope:

- local process lifecycle lives under `scripts/dev/`
- dedicated-server packaging and deployment details remain placeholder-only
- future lanes can add bounded operational scripts without changing service
  ownership

The long-term startup order remains:

1. storage paths available
2. `axon-watch`
3. `control-plane`
4. `console-web`
5. reverse proxy
