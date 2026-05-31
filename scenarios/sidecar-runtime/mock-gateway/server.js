'use strict';

/**
 * Mock Agent Assembly gateway for local development.
 *
 * Implements a minimal subset of the gateway HTTP API:
 *   GET  /health         — health check
 *   POST /v1/tool/call   — evaluate a tool call against a simple policy
 *
 * Replace this container with the real gateway image when you have access.
 */

const http = require('http');

const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

function log(msg) {
  if (LOG_LEVEL !== 'silent') {
    console.log(`[${new Date().toISOString()}] ${msg}`);
  }
}

// Simple inline policy: deny destructive operations; allow everything else.
const DENY_TOOLS = new Set(['delete_file', 'drop_database', 'truncate_table']);

function evaluate(tool) {
  if (DENY_TOOLS.has(tool)) {
    return { decision: 'deny', reason: 'destructive operations are blocked by policy' };
  }
  return { decision: 'allow', reason: 'permitted by default policy' };
}

const server = http.createServer((req, res) => {
  const { method, url } = req;

  // Health check
  if (url === '/health' || url === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'assembly-gateway-mock', version: '0.0.1' }));
    return;
  }

  // Tool call evaluation
  if (method === 'POST' && url === '/v1/tool/call') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let payload = {};
      try { payload = JSON.parse(body); } catch { /* malformed body — treat as empty */ }

      const tool = payload.tool || 'unknown';
      const { decision, reason } = evaluate(tool);
      const auditId = `audit-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      log(`tool=${tool.padEnd(25)} decision=${decision.padEnd(6)} reason=${reason}`);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ decision, reason, audit_id: auditId }));
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found', path: url }));
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  log(`Mock assembly-gateway listening on :${PORT}`);
  log(`Health check: GET http://localhost:${PORT}/health`);
  log(`Tool call:    POST http://localhost:${PORT}/v1/tool/call`);
});
