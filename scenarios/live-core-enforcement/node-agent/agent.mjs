#!/usr/bin/env node
/**
 * Live registration smoke — Node SDK — Agent Assembly examples.
 *
 * Unlike node/custom-tool-policy (and every other node/ example), which wires an
 * in-process `createPolicyGatewayClient` stub with `mode: "sdk-only"` and never
 * touches the network, this driver uses the REAL SDK transport: it imports
 * `initAssembly` from `@agent-assembly/sdk` and registers this agent against a
 * running gateway over the SDK's native gRPC client. There is deliberately no
 * offline fallback here — that absence is the point of the verify-live lane
 * (AAASM-4475): exercise the native-binding + gRPC registration path that
 * AAASM-4467/4468 showed the mock lanes can never reach.
 *
 * The verify-live workflow starts a real `aasm start --mode local` gateway, runs
 * this driver against it, then asserts this agent appears in the gateway's
 * /api/v1/agents REST surface. This driver only has to register and make one
 * governed call; the workflow owns the visibility assertion.
 *
 * Node vs the go-agent / python-agent counterparts: the go SDK's
 * `assembly.Init(...).WrapTools(...)` reuses the Init-established governance
 * client to route a tool's DENY check back through the runtime, and the python
 * SDK deep-imports `RuntimeQueryInterceptor` for the same. The node SDK's public
 * surface exposes neither — `AssemblyContext` does not carry the native check
 * client, and the only exported gateway client is the first-party no-op one — so
 * the node driver's real-transport work is the `initAssembly` registration
 * (which the /api/v1/agents assertion checks), and its one governed call is
 * wired with `withAssembly` in the SDK-family "observe / pass-through" posture:
 * the pre-exec wrapper runs while the real gateway this agent registered against
 * (plus the proxy / eBPF layers) stays the authoritative policy decision-maker.
 *
 * Env:
 *   AA_GATEWAY_URL  gateway endpoint the SDK registers against (gRPC :50051).
 *   AA_AGENT_ID     the id to register under (must match the workflow's assert).
 */
import { createNoopGatewayClient, initAssembly, withAssembly } from "@agent-assembly/sdk";

const gatewayUrl = process.env.AA_GATEWAY_URL || "http://127.0.0.1:50051";
const agentId = process.env.AA_AGENT_ID || "live-smoke-node";

async function main() {
  // initAssembly opens the SDK session and registers the agent with the real
  // gateway over the native gRPC transport. If the native binding is missing
  // (AAASM-4467) or register() is a no-op (AAASM-4468), `registered` comes back
  // false and a stderr warning fires — there is no stub to silently answer for
  // it, which is exactly what verify-live is meant to surface.
  const ctx = await initAssembly({ gatewayUrl, agentId });
  console.log(
    `[live] registered=${ctx.registered} agent "${agentId}" against ${gatewayUrl}`
  );

  // One governed call, wired the same way node/custom-tool-policy wires a
  // bare-SDK tool: define the tool, then wrap it with withAssembly so the
  // pre-exec governance chain runs before the tool body. The gateway client is
  // the SDK's own first-party no-op client (not a hand-rolled policy stub); it
  // puts the wrapper in the pass-through posture described in the header,
  // leaving the gateway this agent registered against authoritative.
  const tools = withAssembly(
    {
      read_file: {
        execute: async (args) => `read ok: ${JSON.stringify(args)}`
      }
    },
    { gatewayClient: createNoopGatewayClient("grpc-sidecar", gatewayUrl), agentId }
  );

  const result = await tools.read_file.execute({ path: "/data/report.csv" });
  console.log(`[live] governed read_file result: ${result}`);

  await ctx.shutdown();
}

try {
  await main();
} catch (err) {
  console.error(err);
  process.exit(1);
}
