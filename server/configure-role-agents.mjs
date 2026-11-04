import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { CODEX_AGENTS_DIR } from "../router/src/paths.mjs";

export const EXECUTION_ROLES = Object.freeze({
  explore: ["Sol", "Read-only code discovery and evidence gathering."],
  execute: ["Sol", "Bounded implementation and complex tests in explicitly owned files."],
  mechanical: ["Luna", "Established mechanical edits, factual documentation and simple checks."],
  visual: ["Terra", "Visual inspection and continuous browser or desktop operations."],
  plan: ["Astra", "Difficult architecture, material trade-offs and proposal challenges."],
  review: ["Astra", "Independent final code review and risk-focused verification."],
});

export function roleAgentDefinition(role) {
  const [model, description] = EXECUTION_ROLES[role];
  return [
    "# Managed by the local Sol-main router role publisher.",
    `name = "router_role_${role}"`,
    `description = ${JSON.stringify(`${description} Fixed ${model}; automatic effort.`)}`,
    'model_provider = "codex-router"',
    `model = "jev/role-${role}"`,
    "",
    'developer_instructions = """',
    "Complete only the bounded task assigned by the parent. Respect user and repository instructions.",
    "Do not delegate further. Do not change the assigned model or take over task priorities.",
    "Only write files or operate resources explicitly assigned to you; other agents may be working.",
    ...(["explore", "plan", "review"].includes(role)
      ? ["Read-only role: do not edit files, commit, push, deploy or operate destructive commands."]
      : []),
    ...(role === "mechanical"
      ? ["Return unresolved semantics or trade-offs to the parent rather than guessing."]
      : []),
    ...(role === "visual"
      ? ["Keep one operator per browser session. Prefer native computer use and return observable evidence."]
      : []),
    "Return findings or changes, evidence with file/line references where applicable, checks run and remaining risks.",
    '"""',
    "",
  ].join("\n");
}

export function configureRoleAgents(agentsDir = CODEX_AGENTS_DIR) {
  mkdirSync(agentsDir, { recursive: true, mode: 0o700 });
  for (const role of Object.keys(EXECUTION_ROLES)) {
    const target = path.join(agentsDir, `router-role-${role}.toml`);
    if (existsSync(target) && !readFileSync(target, "utf8").startsWith(
      "# Managed by the local Sol-main router role publisher.\n",
    )) {
      throw new Error(`Refusing to replace an unmanaged role agent: ${target}`);
    }
  }
  for (const role of Object.keys(EXECUTION_ROLES)) {
    const target = path.join(agentsDir, `router-role-${role}.toml`);
    const temporary = `${target}.tmp.${process.pid}`;
    writeFileSync(temporary, roleAgentDefinition(role), { mode: 0o600 });
    renameSync(temporary, target);
  }
}
