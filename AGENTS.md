# Codex Auto Router

This is an Early Access distribution of Jev Codex Router. Read [README.md](README.md)
for portable setup and [CONTRIBUTING.md](CONTRIBUTING.md) for development and
verification. Preserve upstream license notices and attribution.

## Architecture and Behavior

- `server/` owns classifier calls, bounded routing dossiers, execution roles,
  effort, leases, and native routing telemetry.
- `router/` is the embedded transport fork. No second checkout is required.
- The picker is **Auto (Role Router)**. Internal `jev/*` routes, legacy command
  names, and existing state paths remain stable for compatibility.
- The main model defaults to Sol. Explore/execute default to Sol, mechanical to
  Luna, visual to Terra, and plan/review to Astra. All seven roles are configurable
  independently in `~/.config/codex-auto-router/config.json`.
- Each fixed role independently adapts effort. On the main route only, picker
  high sets a medium floor, xhigh a high floor, and max an xhigh floor.
- Classifier errors retain the assigned model at medium, subject to the main
  floor. Fixed roles fail on exhausted native quota rather than switch providers.
- Classification-only `/v1/route` retains its independent adaptive policy.
  `JEV_EXECUTION_POLICY=adaptive` restores the legacy main policy; it does not
  change worker models or `/v1/route`.
- The executor receives the full canonical Codex request. The selected classifier
  receives only the bounded dossier, which may nevertheless contain private
  content. Never substitute that dossier for executor history.

## Safety Boundaries

Never print or publish credentials, Codex tokens, caller secrets, conversations,
or raw routing logs. Ask for protected credential references, not key values.
ChatGPT tokens must not be sent to the classifier.

Edit source, not generated catalogs, `litellm.yaml`, managed Codex configuration
blocks, or installed runtime artifacts. Keep listeners on loopback. Preserve
authentication even when classification fails.

Keep user settings outside the checkout. Configuration is loaded at service
startup and catalog generation, not per request. Do not restart services while
they are carrying work. Source validation is not deployment validation.

Delegation depends on caller tools, user instructions, and repository rules.
Use only offered agent types. Give workers bounded ownership; retain integration
and acceptance in the main task. A browser session has one active operator.

## Installation and Updates

The complete stack targets macOS, Node.js 22.19+, Python 3.11+, Codex desktop and
CLI, and an authenticated account with access to the configured models. Follow
the selected TypeSafe/Jev or OpenCode Go credential procedure in the README.
Do not claim arbitrary compatible endpoints are supported.

`./install.sh` configures the embedded stack and both launchd services. It asks
separately before reading Codex's login session and before a quota-consuming live
smoke request. Skipping smoke leaves real routing unverified.

`./install.sh --prepare-only` prepares dependencies without configuring services,
credentials, or the user's Codex state. If service management is restricted,
use this mode and have the user run the full installer in Terminal.

`bin/jev-codex-router update` verifies this distribution's remote, requires a clean
tree, fast-forwards the same checkout, and reinstalls. It must never silently
replace this distribution with upstream. The bootstrap defaults to
`~/.local/share/codex-auto-router-source`; `JEV_ROUTER_SOURCE_DIR` can explicitly
select an existing checkout.

Temporary HOME, CODEX_HOME, state directories, labels, or a stub launchctl do
not isolate the launchd user domain. Full install/update/uninstall acceptance
requires a separate OS user or VM. Read [docs/RELEASING.md](docs/RELEASING.md)
before testing installation.

## Verification and Operations

Run credential-free contributor checks from CONTRIBUTING.md and report actual
results and skips. The supported CI matrix is in [docs/SUPPORT.md](docs/SUPPORT.md).
Do not weaken assertions or disable a platform to hide a failure.

After an explicitly authorized installation, run `bin/jev-codex-router doctor`.
Only with live-request consent, run `bin/jev-codex-router smoke`: require a fresh
classifier decision, completed response, matching selected/response models, and
confirmed visible effort. Health or a picker entry alone is insufficient.
Fully reopen Codex to reload its model and agent catalogs.

Local logs under `~/.codex/codex-router/` are private. The CLI `report` command
summarizes routing; `router refresh-catalog` republishes the catalog. Neither
operation proves live model access or classifier quality.

The `jev-router.off` and `jev-router.shadow` sentinels bypass applied classifier
decisions. Fixed-role requests retain their assigned model at medium, with the
main effort floor; legacy adaptive requests retain their separate behavior.
The `jev-router.hide-signature` sentinel hides ordinary reply route headers.
Structured JSON is never prefixed. Debug captures remain private even when
bounded or sanitized.

`uninstall` stops the sidecar and disables its model/provider while retaining
keys and diagnostics. Use `uninstall --revoke-session` only with explicit
authorization to revoke native session sharing.

## Publication

Public documentation and contribution conventions are English. Never publish
personal setup references, private prompt captures, or unreviewed screenshots.
Audit history and commit metadata as well as HEAD. Do not rewrite shared history,
commit, push, or change repository visibility without the required explicit
approval. An Early Access label does not waive the release acceptance gates.
