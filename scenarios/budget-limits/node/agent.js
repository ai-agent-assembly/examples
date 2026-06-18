#!/usr/bin/env node
/**
 * Budget-limits scenario — Agent Assembly examples
 *
 * Demonstrates how Agent Assembly enforces budget guardrails on governed tool calls.
 * No API keys or external services are required to run this example.
 *
 * Usage:
 *   node agent.js
 */

'use strict';

// Per-call costs matching policy.yaml
const TOOL_COSTS = {
  web_search: 0.05,
  query_database: 0.1,
  call_external_api: 0.2,
  generate_report: 0.25,
};

// Session budget ceiling matching policy.yaml budget.max_cost
const BUDGET_LIMIT = 0.5;

// ---------------------------------------------------------------------------
// Minimal Agent Assembly SDK stubs used in this offline example.
// In a real integration replace these with:
//   const { AssemblyClient, BudgetPolicy } = require('@agent-assembly/sdk');
// ---------------------------------------------------------------------------

class BudgetExceededError extends Error {
  constructor(message) {
    super(message);
    this.name = 'BudgetExceededError';
  }
}

class BudgetTracker {
  constructor(maxCost) {
    this.maxCost = maxCost;
    this._spent = 0;
  }

  get spent() {
    return this._spent;
  }

  get remaining() {
    return Math.max(0, this.maxCost - this._spent);
  }

  charge(cost) {
    this._spent += cost;
  }

  status() {
    const pct = Math.round((this._spent / this.maxCost) * 100);
    return `spent=$${this._spent.toFixed(2)} / limit=$${this.maxCost.toFixed(2)} (${pct}%)`;
  }
}

class AssemblyClient {
  constructor(agentId, budget) {
    this.agentId = agentId;
    this._budget = budget;
  }

  callTool(tool, inputs = {}) {
    const cost = TOOL_COSTS[tool] ?? 0.01;

    if (cost > this._budget.remaining) {
      throw new BudgetExceededError(
        `Budget exceeded: tool '${tool}' costs $${cost.toFixed(2)} but ` +
        `only $${this._budget.remaining.toFixed(2)} remains ` +
        `(spent=$${this._budget.spent.toFixed(2)} / limit=$${this._budget.maxCost.toFixed(2)})`,
      );
    }

    this._budget.charge(cost);
    console.log(
      `  [BUDGET] charged $${cost.toFixed(2)} for '${tool}'  →  ${this._budget.status()}`,
    );
    return { status: 'ok', tool, data: `<result of ${tool}>` };
  }
}

// ---------------------------------------------------------------------------
// Example agent
// ---------------------------------------------------------------------------

function run() {
  console.log('=== Agent Assembly — Budget Limits Example ===\n');
  console.log(`Policy: max_cost=$${BUDGET_LIMIT.toFixed(2)} per session (see policy.yaml)\n`);

  const budget = new BudgetTracker(BUDGET_LIMIT);
  const client = new AssemblyClient('example-agent-001', budget);

  const calls = [
    { tool: 'web_search',        inputs: { query: 'latest AI news' } },       // $0.05 → $0.05
    { tool: 'query_database',    inputs: { table: 'customers' } },             // $0.10 → $0.15
    { tool: 'call_external_api', inputs: { endpoint: '/v1/report' } },        // $0.20 → $0.35
    { tool: 'web_search',        inputs: { query: 'weather forecast' } },     // $0.05 → $0.40
    { tool: 'generate_report',   inputs: { format: 'pdf' } },                 // $0.25 → exceeds $0.50
    { tool: 'call_external_api', inputs: { endpoint: '/v2/sync' } },          // $0.20 → blocked
  ];

  console.log('--- Running tool calls against budget ---\n');

  for (const { tool, inputs } of calls) {
    const cost = TOOL_COSTS[tool] ?? 0.01;
    const argsStr = Object.entries(inputs)
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(', ');
    console.log(`  → ${tool}(${argsStr})  [cost=$${cost.toFixed(2)}]`);
    try {
      const result = client.callTool(tool, inputs);
      console.log(`    ✓ allowed  →  ${JSON.stringify(result)}\n`);
    } catch (err) {
      console.log(`    ✗ denied   →  ${err.message}\n`);
    }
  }

  console.log(`\nFinal budget state: ${budget.status()}`);
}

run();
