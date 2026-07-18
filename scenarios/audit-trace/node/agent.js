#!/usr/bin/env node
/**
 * Audit-trace scenario — Agent Assembly examples
 *
 * Demonstrates how Agent Assembly records audit events for governed tool calls.
 * No API keys or external services are required to run this example.
 *
 * Usage:
 *   node agent.js
 */

'use strict';

const { randomUUID } = require('node:crypto');

// ---------------------------------------------------------------------------
// The classes below are LOCAL stand-ins so this file runs offline with no
// install — they are NOT the SDK's public API. In a real integration you do not
// build the audit log in the agent: every governed tool call is recorded
// GATEWAY-side (the gateway emits the audit event with the agent id, tool,
// decision and reason). You wrap your tools with `withAssembly` and the trace is
// then read back from the gateway / dashboard, not assembled client-side:
//
//   const { withAssembly } = require('@agent-assembly/sdk');
//   const governed = withAssembly(tools, { gatewayClient, agentId: 'my-agent' });
//
// There is no `AssemblyClient`/`AuditLogger` export to import — the gateway owns
// the audit trail.
// ---------------------------------------------------------------------------

const Decision = Object.freeze({
  ALLOW: 'allow',
  DENY: 'deny',
  APPROVAL_REQUIRED: 'approval_required',
});

class AuditRecord {
  constructor({ agentId, tool, decision, reason, inputs = {}, outputs = {} }) {
    this.event_id = randomUUID();
    this.timestamp = new Date().toISOString();
    this.agent_id = agentId;
    this.tool = tool;
    this.decision = decision;
    this.reason = reason;
    this.inputs = inputs;
    this.outputs = outputs;
  }

  serialize() {
    const { event_id, timestamp, agent_id, tool, decision, reason, inputs, outputs } = this;
    return JSON.stringify(
      { event_id, timestamp, agent_id, tool, decision, reason, inputs, outputs },
      null,
      2,
    );
  }
}

class AuditLogger {
  constructor() {
    this._records = [];
  }

  append(record) {
    this._records.push(record);
    const tool = record.tool.padEnd(20);
    const decision = record.decision.padEnd(18);
    console.log(
      `[AUDIT] ${record.timestamp}  tool=${tool}  decision=${decision}  reason=${record.reason}`,
    );
  }

  records() {
    return [...this._records];
  }
}

const POLICY = {
  read_file: [Decision.ALLOW, 'read operations are permitted by default'],
  delete_file: [Decision.DENY, 'destructive operations are blocked by policy'],
  send_email: [
    Decision.APPROVAL_REQUIRED,
    'outbound communication requires human approval',
  ],
};

class AssemblyClient {
  constructor(agentId, logger) {
    this.agentId = agentId;
    this._logger = logger;
  }

  callTool(tool, inputs = {}) {
    const [decision, reason] = POLICY[tool] ?? [Decision.ALLOW, 'no matching policy rule'];

    const record = new AuditRecord({ agentId: this.agentId, tool, decision, reason, inputs });

    if (decision === Decision.ALLOW) {
      record.outputs = { status: 'ok', data: `<result of ${tool}>` };
      this._logger.append(record);
      return record.outputs;
    }

    this._logger.append(record);

    if (decision === Decision.DENY) {
      throw new Error(`Tool '${tool}' denied: ${reason}`);
    }

    throw new Error(`Tool '${tool}' requires approval before proceeding: ${reason}`);
  }
}

// ---------------------------------------------------------------------------
// Example agent
// ---------------------------------------------------------------------------

function run() {
  console.log('=== Agent Assembly — Audit / Trace Example ===\n');

  const audit = new AuditLogger();
  const client = new AssemblyClient('example-agent-001', audit);

  const calls = [
    { tool: 'read_file', inputs: { path: '/data/report.csv' } },
    { tool: 'delete_file', inputs: { path: '/data/important.csv' } },
    { tool: 'send_email', inputs: { to: 'team@example.com', subject: 'Quarterly Report' } },
  ];

  console.log('--- Calling governed tools ---\n');

  for (const { tool, inputs } of calls) {
    const argsStr = Object.entries(inputs)
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(', ');
    console.log(`  → ${tool}(${argsStr})`);
    try {
      const result = client.callTool(tool, inputs);
      console.log(`    ✓ allowed  →  ${JSON.stringify(result)}\n`);
    } catch (err) {
      console.log(`    ✗ blocked  →  ${err.message}\n`);
    }
  }

  console.log('\n--- Full audit trace (JSON) ---\n');
  for (const record of audit.records()) {
    console.log(record.serialize());
    console.log();
  }

  console.log(`Total events recorded: ${audit.records().length}`);
}

run();
