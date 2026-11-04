---
name: jev-codex-router
description: Install, update, verify, diagnose, or uninstall Codex Auto Router, the Early Access role-based Codex distribution.
---

# Codex Auto Router

Use this distribution's [repository](https://github.com/roywong10/codex-auto-router),
not upstream's installer. The legacy plugin name, CLI, and internal `jev/*`
identifiers remain for compatibility. The picker is **Auto (Role Router)**.
Installing the plugin alone does not configure credentials or start services.

## Setup

Read the checkout's README and AGENTS.md before operations. Require macOS,
Node.js 22.19+, Python 3.11+, Codex desktop and CLI, and the user's authenticated
Codex account. Model access is not guaranteed.

Clone `roywong10/codex-auto-router`. Choose either TypeSafe/Jev or OpenCode Go
using the README credential-reference procedure. Ask only for protected key-file
paths or Keychain references, never actual keys. Never expose tokens, caller
secrets, auth.json contents, or private logs.

Run `./install.sh` only when installation is authorized. It configures local
providers and launchd services, asks before reading the Codex login session, and
separately asks before a quota-consuming smoke request. Tokens are not sent to
the classifier. If service management is restricted, use `--prepare-only` and
have the user complete installation in Terminal. Do not bypass restrictions.

Temporary HOME, state paths, or command stubs do not isolate launchd. Full
installation fixtures require a separate OS user or VM.

## Routing

Defaults: main/explore/execute use Sol, mechanical uses Luna, visual uses Terra,
and plan/review use Astra. All seven roles are independently configurable in
`~/.config/codex-auto-router/config.json`; consult the README for supported
models. Settings load at startup and catalog generation, not per request.

Each role automatically selects effort. Main-thread picker high sets a medium
floor, xhigh a high floor, and max an xhigh floor. Workers do not inherit this
preference. Classifier errors keep the assigned model at medium, subject to the
main floor; fixed roles do not silently switch providers on quota exhaustion.
Classification-only `/v1/route` retains its separate adaptive model policy.

The executor receives full canonical context; the classifier receives a bounded
dossier that may still contain sensitive text. Cache evidence is an optimization,
not conversation storage. Delegate only when caller tools and instructions allow
it. A browser session has one active operator.

## Acceptance and Maintenance

Run `bin/jev-codex-router doctor` after installation. Only with live-request
consent, run `bin/jev-codex-router smoke`: require fresh `opencode-go` or `jev`
classification, a completed response, matching selected/response models, and
confirmed visible effort. Skipped smoke, technical fallback, HTTP health, or a
picker entry is not end-to-end acceptance.

Wait for active tasks before restarting services. Fully reopen Codex to reload
model and role-agent catalogs. A published catalog does not prove model access.

`bin/jev-codex-router update` requires a clean checkout, verifies the fork remote,
fast-forwards that same checkout, and reruns installation. Do not update from
upstream over this distribution. Keep user configuration outside Git.

`uninstall` disables the sidecar and model/provider while retaining keys and
diagnostics. Use `uninstall --revoke-session` only with explicit authorization.
Review and redact diagnostics locally; never upload them automatically.
