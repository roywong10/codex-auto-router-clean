// Idempotently declare jev/auto in the embedded router's protected user-model
// overlay. Existing user-curated routes are preserved.
import {
  readUserModels,
  writeUserModels,
} from "../router/src/user-models.mjs";
import { configureRoleAgents, EXECUTION_ROLES } from "./configure-role-agents.mjs";

const decisionProvider = process.env.JEV_DECISION_PROVIDER || "typesafe";
if (!["typesafe", "opencode-go"].includes(decisionProvider)) {
  throw new Error("Unsupported JEV_DECISION_PROVIDER");
}
const usesDeepSeek = decisionProvider === "opencode-go";

export const JEV_MODEL = Object.freeze({
  slug: "jev/auto",
  gatewayModel: "jev-auto",
  compHash: "jev-auto-user-v1",
  upstreamModel: "auto",
  provider: "jev",
  listed: true,
  displayName: "Auto (Role Router)",
  description:
    `Fixed GPT-6.1 Sol main agent; automatic effort by ${usesDeepSeek ? "DeepSeek V4.1 Flash via OpenCode Go" : "Jev"}. Dedicated Sol, Luna, Terra and Astra role agents.`,
  priority: 95,
  defaultEffort: "medium",
  reasoningLevels: [
    { effort: "low", description: "Quick reasoning" },
    { effort: "medium", description: "Balanced reasoning" },
    { effort: "high", description: "Deep reasoning" },
    { effort: "xhigh", description: "Extended reasoning" },
    { effort: "max", description: "Maximum reasoning" },
  ],
  contextWindow: 258400,
  autoCompact: 219640,
  searchTool: { mode: "hosted" },
  supportsSearchHistory: true,
  inputModalities: ["text", "image"],
});

const existing = readUserModels();
const roleModels = Object.entries(EXECUTION_ROLES).map(([role, [model, description]]) => ({
  ...JEV_MODEL,
  slug: `jev/role-${role}`,
  gatewayModel: `jev-role-${role}`,
  compHash: `jev-role-${role}-user-v1`,
  upstreamModel: `role/${role}`,
  displayName: `${model} ${role} (auto effort)`,
  description,
  priority: 70,
}));
const managedSlugs = new Set([JEV_MODEL.slug, ...roleModels.map((model) => model.slug)]);
const next = [
  ...existing.filter((model) => !managedSlugs.has(model?.slug)),
  JEV_MODEL,
  ...roleModels,
];
configureRoleAgents();
writeUserModels(next);
process.stdout.write(`${JSON.stringify({
  configured: JEV_MODEL.slug,
  preservedModels: existing.filter((model) => !managedSlugs.has(model?.slug)).length,
  roles: Object.keys(EXECUTION_ROLES),
})}\n`);
