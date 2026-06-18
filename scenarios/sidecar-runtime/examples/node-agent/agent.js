#!/usr/bin/env node
/**
 * Sidecar-runtime scenario — Agent Assembly examples
 *
 * Demonstrates running an AI agent against a local Agent Assembly runtime sidecar.
 * Connects to the gateway at ASSEMBLY_GATEWAY_URL when set; falls back to an
 * offline policy when the gateway is not available.
 *
 * Usage (with local runtime):
 *   bash scripts/start.sh
 *   export ASSEMBLY_GATEWAY_URL=http://localhost:8080
 *   node examples/node-agent/agent.js
 *
 * Usage (offline, no Docker needed):
 *   node examples/node-agent/agent.js
 */

'use strict';

const http = require('node:http');

// ---------------------------------------------------------------------------
// Gateway client — tries the local runtime, falls back to an offline policy
// ---------------------------------------------------------------------------

const GATEWAY_URL = (process.env.ASSEMBLY_GATEWAY_URL || '').replace(/\/$/, '');

const OFFLINE_POLICY = {
  delete_file:   { decision: 'deny',  reason: 'destructive operations are blocked by policy' },
  drop_database: { decision: 'deny',  reason: 'destructive operations are blocked by policy' },
};

function callGateway(tool, inputs) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ tool, inputs });
    const url = new URL(`${GATEWAY_URL}/v1/tool/call`);

    const req = http.request(
      {
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
      },
      res => {
        let data = '';
        res.on('data', chunk => { data += chunk; });
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch { reject(new Error('Invalid JSON response')); }
        });
      },
    );

    req.setTimeout(5000, () => { req.destroy(); reject(new Error('Request timed out')); });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function callOffline(tool) {
  return OFFLINE_POLICY[tool] ?? { decision: 'allow', reason: 'permitted by default policy' };
}

async function evaluateTool(tool, inputs) {
  if (GATEWAY_URL) {
    try {
      return await callGateway(tool, inputs);
    } catch (err) {
      console.log(`  [WARN] Gateway unreachable (${err.message}); falling back to offline policy.`);
    }
  }
  return callOffline(tool);
}

// ---------------------------------------------------------------------------
// Example agent
// ---------------------------------------------------------------------------

async function run() {
  console.log('=== Agent Assembly — Sidecar Runtime Example ===\n');

  if (GATEWAY_URL) {
    console.log(`Gateway: ${GATEWAY_URL}  (connected)\n`);
  } else {
    console.log('Gateway: not configured — running in offline mode');
    console.log('         Set ASSEMBLY_GATEWAY_URL=http://localhost:8080 to connect.');
    console.log('         See scripts/start.sh to start the local runtime.\n');
  }

  const calls = [
    { tool: 'read_file',   inputs: { path: '/data/report.csv' } },
    { tool: 'delete_file', inputs: { path: '/data/important.csv' } },
  ];

  const mode = GATEWAY_URL ? 'via the local runtime' : 'via offline policy';
  console.log(`--- Calling governed tools ${mode} ---\n`);

  for (const { tool, inputs } of calls) {
    const argsStr = Object.entries(inputs)
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(', ');
    console.log(`  → ${tool}(${argsStr})`);

    const response = await evaluateTool(tool, inputs);
    const { decision = 'unknown', reason = '', audit_id: auditId } = response;

    if (decision === 'allow') {
      console.log(`  [GATEWAY] decision=allow   reason=${reason}`);
      console.log(`    ✓ allowed\n`);
    } else {
      console.log(`  [GATEWAY] decision=deny    reason=${reason}`);
      console.log(`    ✗ denied\n`);
    }

    if (auditId) {
      console.log(`  Audit ID: ${auditId}`);
    }
  }

  console.log(`Total tool calls: ${calls.length}`);
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
