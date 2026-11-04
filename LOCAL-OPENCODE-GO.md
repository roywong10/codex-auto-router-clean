# OpenCode Go Integration

This file replaces historical machine-specific adaptation notes. Use
[README.md](README.md) for installation and current role configuration; local
acceptance anecdotes are not portable support or performance guarantees.

OpenCode Go is an optional classifier, not the execution provider. The
configured Codex role model still receives the full canonical request through
the authorized local Codex session. ChatGPT tokens are not sent to OpenCode Go.
The classifier receives a bounded task dossier that may contain private text.

Select `JEV_DECISION_PROVIDER=opencode-go` and supply the nonsecret
`OPENCODE_GO_KEYCHAIN_SERVICE` and `OPENCODE_GO_KEYCHAIN_ACCOUNT` references.
The installer persists references, not a plaintext API key. Use your own
protected login-keychain item; never commit machine-specific credential
references or copy key values into shell arguments.

The adapter uses DeepSeek V4.1 Flash through the OpenCode Go endpoint, refuses
redirects, and validates classifier choices. Provider availability and model
allowance remain external dependencies.

Fixed execution roles request independent effort and lease choices.
Classifier failure keeps the assigned model at medium, subject to the main
effort floor. The separate classification-only `/v1/route` consumer retains
adaptive model selection and returns errors rather than a fabricated decision.
Generic TypeSafe `/ask` is unavailable in Go mode.

Logs label fresh Go decisions `decision_source=opencode-go`; historical `jev_*`
field names remain for compatibility. A healthy process or a lease-only result
does not prove a new classifier request succeeded. Only an explicitly authorized
live smoke check establishes connectivity for that installed instance.

Earlier versions of this file contained local paths and installation history.
Changing the current document does not remove prior Git versions. Review
history and metadata before publication; history rewriting requires separate
approval.
