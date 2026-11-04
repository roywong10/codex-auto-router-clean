# Support and test matrix

Last reviewed: 2026-11-04.

## Product support

The complete Codex Auto Router Early Access stack targets macOS with the
Codex desktop application, Node.js 22.19 or newer, and Python 3.11 or newer.
The installer and background-service contract are macOS-specific because they
install launchd services and publish the model into the local Codex desktop
configuration.

The real CLI contract is pinned to the versions below. A newer desktop may bundle
a different CLI and requires separate requalification; a visible picker does not
prove protocol compatibility. Do not infer universal Codex-version support from
passing the pinned contract.

The embedded router under `router/` retains inherited cross-platform code.
This distribution requires its runtime and state-management suite on Ubuntu
and macOS with Node.js 24 in CI. Ubuntu validates portable behavior; it does
not make the root launchd installer supported on Linux.

Windows is outside this distribution's Early Access support and required CI
matrix. Its inherited implementation and tests remain in the source tree, but
are not qualified for use. The Windows run for candidate `60e93d2` did not
complete successfully: the first attempt was cancelled and its retry ended
after approximately 60 minutes. Removing that lane does not resolve its
performance problem. Restoring Windows support requires investigation and a
successful complete Windows suite.

## Required CI lanes

| Lane | Runtime | What it proves |
| --- | --- | --- |
| Jev server | Ubuntu / Python 3.11 | Minimum supported Python and portable policy/relay behavior |
| Jev server | macOS / Python 3.12 | Primary product OS and a current Python runtime |
| Embedded router | Ubuntu, macOS / Node.js 24 | Portable fork behavior, state safety, and the tested platform branches; no Windows qualification |
| Browser panel | Ubuntu / Playwright Chromium | Browser UI tests execute instead of silently skipping for a missing browser |
| Codex app-server contract | Ubuntu / Codex CLI `0.155.0-alpha.9.2` and `0.159.2` | Each real, known Codex binary completes both login-free provider configurations |

The Codex contract lane sets `CODEX_ROUTER_REQUIRE_REAL_CODEX=1`; absence of the
binary is a failure, never a skip. It also checks the exact CLI version before
running the fixture. Updating that pin is a deliberate compatibility change:
run the integration locally, review request and WebSocket behavior, then update
the workflow and this document together.

Codex 0.155 may establish two authenticated WebSocket connections after a
provider-preserving configuration rewrite. The fixture accepts that bounded
reconnect only when exactly one connection relays `response.create` and the
mock upstream receives exactly one model request.

## Optional and live coverage

Routine pull-request CI never uses TypeSafe credits, ChatGPT credentials, or
real model-provider keys. Provider compatibility and the installed launchd
stack remain explicit local/release checks:

```bash
PYTHONPATH=server python3 -m unittest discover -s server -p 'test_*.py'
(cd router && npm run check && npm test)
python3 server/smoke.py
```

For a local browser-panel run, install the locked Playwright browser once:

```bash
cd router
npx playwright install chromium
```

On Linux CI, use `npx playwright install --with-deps chromium`.
