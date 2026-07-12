#!/usr/bin/env node
/**
 * Live registration smoke — Node SDK — Agent Assembly examples.
 *
 * Unlike node/custom-tool-policy (and every other node/ example), which wires an
 * in-process `createPolicyGatewayClient` stub with `mode: "sdk-only"` and never
 * touches the network, this driver uses the REAL SDK transport: it imports
 * `initAssembly` from `@agent-assembly/sdk` and registers this agent against a
 * running gateway over the SDK's native client. There is deliberately no offline
 * fallback here — that absence is the point of the verify-live lane (AAASM-4475):
 * exercise the native-binding + gRPC registration path that AAASM-4467/4468
 * showed the mock lanes can never reach.
 *
 * The verify-live workflow starts a real `aasm start --mode local` gateway, runs
 * this driver against it, then asserts this agent appears in the gateway's
 * /api/v1/agents REST surface. This driver only has to init/register and make one
 * governed call; the workflow owns the visibility assertion.
 *
 * Env:
 *   AA_GATEWAY_URL  gateway endpoint the SDK registers against (gRPC :50051).
 *   AA_AGENT_ID     the id to register under (must match the workflow's assert).
 */
import { initAssembly } from "@agent-assembly/sdk";

const gatewayUrl = process.env.AA_GATEWAY_URL || "http://127.0.0.1:50051";
const agentId = process.env.AA_AGENT_ID || "live-smoke-node";

async function main() {
  // initAssembly opens the SDK session and registers the agent with the real
  // gateway. If the native binding is missing (AAASM-4467) or register() is a
  // no-op (AAASM-4468), this is where verify-live is meant to go red — there is
  // no stub to silently answer for it.
  const ctx = await initAssembly({ gatewayUrl, agentId });
  console.log(`[live] registered agent "${agentId}" against ${gatewayUrl}`);

  // One governed call over the real transport. The SDK client (not an in-process
  // stub) forwards the check to the gateway.
  const result = await ctx.client.callTool("read_file", { path: "/data/report.csv" });
  console.log(`[live] governed read_file result: ${JSON.stringify(result)}`);

  if (typeof ctx.close === "function") {
    await ctx.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
