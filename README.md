# Codex Auto Router

**Early Access.** Interfaces and installation workflows may change. The complete
stack currently targets macOS; the embedded router's cross-platform tests do not
establish Linux or Windows installation support. Keep configuration backups.
The complete install, update, and uninstall workflow has not yet been validated
in a fresh macOS user account or VM. Treat this as experimental software, not a
production-qualified installer.

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
| Explore / Execute: scoped discovery and implementation | Sol, configurable |
| Mechanical: established edits and simple checks | Luna, configurable |
| Visual: visual inspection, browser and desktop workflows | Terra, configurable |
| Plan / Review: difficult architecture and independent review | Astra, configurable |

Each worker independently adapts effort. Delegation depends on caller tools,
user instructions, and repository rules. A browser session has one operator.
Classifier failure keeps the assigned model at Medium.
Fixed roles fail explicitly on exhausted native quota instead of silently
changing providers.

## Requirements

- macOS, Codex desktop and CLI, and an authenticated Codex account.
- Node.js 22.19+ and Python 3.11+.
- Your own classifier credentials and access to the configured execution models.

See the [support matrix](docs/SUPPORT.md) for pinned Codex CLI contract versions.
Newer desktop or CLI builds require separate compatibility validation.

The installer changes local configuration and installs background services.
Review it before running. Contributor tests do not require installation.

## Installation

1. Install the prerequisites above and sign in to Codex.
2. Clone this repository.
3. Choose **one** classifier setup below, then run its installation commands.
4. Reopen Codex and complete the verification below.

Clone and enter the checkout (GitHub CLI is not required):

```sh
git clone https://github.com/roywong10/codex-auto-router-clean.git
cd codex-auto-router-clean
```

The role configuration is optional. You can start with the defaults; your account
must have access to those models, or you must configure accessible supported
models before installation. This project does not grant model access.

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

### If Setup Does Not Work

- If the picker is missing, fully quit and reopen Codex, then run
  `bin/jev-codex-router doctor` from the checkout.
- If authentication fails, verify the chosen classifier's protected key-file
  path or Keychain service/account references. Never paste a key into an issue.
- If a role's model is unavailable, choose an accessible supported model in the
  configuration below. Fixed roles do not silently switch models.
- When reporting a problem, include your macOS, Node.js, Python, and Codex CLI
  versions, the source commit, and a redacted error summary. Do not attach raw
  logs, conversations, credential files, or full configuration.

## Role Model Configuration

Create `~/.config/codex-auto-router/config.json`:

```json
{
  "execution": {
    "main_model": "gpt-6.1-sol",
    "explore_model": "gpt-6.1-sol",
    "execute_model": "gpt-6.1-sol",
    "mechanical_model": "gpt-6-luna",
    "visual_model": "gpt-6.1-terra",
    "plan_model": "gpt-6-astra",
    "review_model": "gpt-6-astra"
  }
}
```

Supported values: `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol`, `gpt-6-astra`.
Every field is optional; omitted roles use the defaults shown above. Each role
can be overridden independently, including explore versus execute and plan
versus review. Invalid JSON, unknown fields, and unsupported models fail
explicitly. Existing main-only configuration remains valid. Model selection
does not change a role's permissions or its independently automatic effort.
The catalog retains its existing shared conservative context limits; selecting
a model does not expand the advertised window.

Configuration loads at service startup and catalog generation, not per request.
Wait until routed tasks are idle, then run `./install.sh` from your configured
terminal. This republishes the catalog and restarts services, clearing routing
leases. Reopen Codex to reload the catalog. User settings stay outside Git.

## Effort Preference

The main-thread picker is a preference, not a floor or ceiling. The classifier
receives the selected effort and considers it alongside remaining task difficulty.
XHigh/Max preferences favor deeper reasoning for complex investigations,
architecture, and synthesis. Clearly simple steps can still use Medium or Low;
hard work can exceed a lower preference. These are classifier instructions, not
a guarantee of any particular choice.

Workers independently choose effort without inheriting the main preference.
Changing preference isolates routing leases so the previous preference's
decision is not reused. Classifier failure and empty-completion technical
recovery use Medium. The service cannot distinguish an app-supplied default
from the same manual selection.

## Operations

```sh
bin/jev-codex-router report --days 7
bin/jev-codex-router router refresh-catalog
bin/jev-codex-router uninstall
```

Use `uninstall --revoke-session` only to revoke native sharing. Uninstall retains
local keys and diagnostics. Logs under `~/.codex/codex-router/` are private:
`depth` records classifier effort, `effort_preference` the preference, and `effort`
the applied value. Never upload raw logs or conversations.

To update a clean checkout, wait for tasks to finish and run:

```sh
bin/jev-codex-router update
```

The updater requires a clean checkout, verifies that its remote is this
distribution, updates that same checkout with a fast-forward merge, and reruns
installation. It does not switch to upstream or a second checkout. Review
upstream changes separately. Go mode does not support generic `/ask`; classification-only
`/v1/route` retains its independent adaptive policy.

## Contributing and Security

See [CONTRIBUTING.md](CONTRIBUTING.md) for English contribution conventions,
offline tests, ownership boundaries, and review expectations.
See [SECURITY.md](SECURITY.md) for security reporting guidance.
See [release preparation](docs/RELEASING.md) for acceptance gates and
[support](docs/SUPPORT.md) for the validation matrix. Early Access is not a
guarantee of model access, routing quality, savings, or production suitability.
