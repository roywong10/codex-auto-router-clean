# Codex Auto Router

A local Codex router with a stable main model, specialist role agents, and
adaptive reasoning effort. Pick the execution model; let a classifier adjust
effort for the remaining work.

An experimental, independently modified distribution of
[Jev Codex Router](https://github.com/ericwanderlust/jev-codex-router).
The embedded transport fork lives in `router/`; no second checkout is needed.
See [ROUTER_FORK.md](ROUTER_FORK.md) and [LICENSE](LICENSE) for provenance and
retained MIT notices. No quality, savings, cache-hit, or account-access guarantee
is implied.

## How It Works

The picker name is **Auto (Role Router)**. Internal `jev/auto` identifiers,
legacy CLI names, and state paths remain stable for compatibility.

The classifier receives a bounded task dossier. The executor receives the full
canonical Codex request through your authorized local Codex session. ChatGPT
tokens are not sent to the classifier.

Supported classifiers are **TypeSafe/Jev** and **OpenCode Go**, currently using
DeepSeek V4.1 Flash. Arbitrary compatible API endpoints are not yet supported.

| Execution role | Default model |
| --- | --- |
| Main: requirements, implementation, integration, acceptance | Sol, configurable |
| Explore / Execute: scoped discovery and implementation | Sol |
| Mechanical: established edits and simple checks | Luna |
| Visual: visual inspection, browser and desktop workflows | Terra |
| Plan / Review: difficult architecture and independent review | Astra |

Each worker independently adapts effort. Delegation depends on caller tools,
user instructions, and repository rules. A browser session has one operator.
Classifier failure keeps the assigned model at Medium, subject to the main
floor. Fixed roles fail explicitly on exhausted native quota instead of silently
changing providers.

## Requirements

- macOS, Codex desktop and CLI, and an authenticated Codex account.
- Node.js 22.19+ and Python 3.11+.
- Your own classifier credentials and access to the configured execution models.

The installer changes local configuration and installs background services.
Review it before running. Contributor tests do not require installation.

## Installation

Clone this repository and enter the checkout:

```sh
gh repo clone roywong10/codex-auto-router
cd codex-auto-router
```

### OpenCode Go

In macOS Keychain Access, create a password item in your login keychain:

| Field | Value |
| --- | --- |
| Name / service | `codex-router/opencode-go` |
| Account | Your macOS username |
| Password | Your raw OpenCode Go API key |

Do not put keys into shell arguments, shell history, issues, or this repository.
The following variables contain references, not secrets:

```sh
export JEV_DECISION_PROVIDER=opencode-go
export OPENCODE_GO_KEYCHAIN_SERVICE=codex-router/opencode-go
export OPENCODE_GO_KEYCHAIN_ACCOUNT="$USER"
./install.sh
```

Existing Keychain items can be reused by specifying their actual service and
account. Approve the operating system access prompt as appropriate. Installation
persists these references for the service. Go mode needs no TypeSafe key.

### TypeSafe

Store your raw Jev key in an owner-only file outside the checkout (`chmod 600`):

```sh
export JEV_DECISION_PROVIDER=typesafe
export JEV_API_KEY_FILE="/absolute/path/to/protected-key-file"
./install.sh
```

### Consent and Verification

Installation separately asks permission to share your local Codex login session
and to send one quota-consuming smoke request. Skipping smoke does not prevent
installation, but leaves real routing unverified.

Fully quit and reopen Codex, then select **Auto (Role Router)**. From a terminal
with the same provider references configured:

```sh
bin/jev-codex-router doctor
bin/jev-codex-router smoke
```

Smoke must show a completed response, matching selected and response models,
effort, and a fresh `opencode-go` or `jev` classifier decision. A picker entry,
health response, or technical fallback alone is not end-to-end verification.

## Main Model Configuration

Create `~/.config/codex-auto-router/config.json`:

```json
{
  "execution": {
    "main_model": "gpt-6.1-sol"
  }
}
```

Supported values: `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol`, `gpt-6-astra`.
Missing configuration defaults to Sol. Invalid JSON, unknown fields, and
unsupported models fail explicitly. Worker assignments remain unchanged.
The catalog retains its existing shared conservative context limits; selecting
a model does not expand the advertised window.

Configuration loads at service startup and catalog generation, not per request.
Wait until routed tasks are idle, then run `./install.sh` from your configured
terminal. This republishes the catalog and restarts services, clearing routing
leases. Reopen Codex to reload the catalog. User settings stay outside Git.

## Effort Preference

| Picker choice | Main-thread minimum |
| --- | --- |
| Low / Medium / absent | Low: unrestricted automatic selection |
| High | Medium |
| XHigh | High |
| Max | XHigh |

Applied effort is the higher of automatic effort and the floor, including lease
reuse and technical recovery. Workers do not inherit this floor. The service
cannot distinguish an app-supplied default from the same manual selection.

## Operations

```sh
bin/jev-codex-router report --days 7
bin/jev-codex-router router refresh-catalog
bin/jev-codex-router uninstall
```

Use `uninstall --revoke-session` only to revoke native sharing. Uninstall retains
local keys and diagnostics. Logs under `~/.codex/codex-router/` are private:
`depth` records classifier effort, `effort_floor` the preference, and `effort`
the applied value. Never upload raw logs or conversations.

To update a clean checkout, wait for tasks to finish and run:

```sh
git pull --ff-only origin main
./install.sh
```

Do not use the inherited `bin/jev-codex-router update` or upstream bootstrap for
this distribution: they remain bound to upstream. Review upstream changes
separately. Go mode does not support generic `/ask`; classification-only
`/v1/route` retains its independent adaptive policy.

## Contributing and Security

See [CONTRIBUTING.md](CONTRIBUTING.md) for English contribution conventions,
offline tests, ownership boundaries, and review expectations.
See [SECURITY.md](SECURITY.md) for security reporting guidance.
Legacy [local adaptation notes](LOCAL-OPENCODE-GO.md) record installation-specific
history, not a portable setup procedure.
