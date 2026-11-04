import assert from "node:assert/strict";
import test from "node:test";
import { injectSessionModelForSpawnCalls } from "../src/namespace-relay.mjs";

test("fixed role agents retain their agent-file model instead of inheriting Auto", () => {
  for (const role of ["explore", "execute", "mechanical", "visual", "plan", "review"]) {
    for (const identity of [
      { namespace: "collaboration", name: "spawn_agent" },
      { name: "collaboration__spawn_agent" },
    ]) {
      const item = { type: "function_call", ...identity, arguments: JSON.stringify({
        agent_type: `router_role_${role}`, message: "bounded task",
        model: "gpt-6.1-sol", reasoning_effort: "low",
      }) };
      const next = injectSessionModelForSpawnCalls(item, "jev/auto");
      assert.deepEqual(JSON.parse(next.arguments), {
        agent_type: `router_role_${role}`, message: "bounded task",
      });
    }
  }
});

test("role inheritance exception does not affect other parents or unknown agents", () => {
  const item = { type: "function_call", namespace: "collaboration", name: "spawn_agent",
    arguments: JSON.stringify({ agent_type: "router_role_review", message: "task" }) };
  assert.equal(JSON.parse(injectSessionModelForSpawnCalls(item, "other/model").arguments).model,
    "other/model");
  const unknown = { ...item, arguments: JSON.stringify({ agent_type: "my_agent", message: "task" }) };
  assert.equal(JSON.parse(injectSessionModelForSpawnCalls(unknown, "jev/auto").arguments).model,
    "jev/auto");
});
