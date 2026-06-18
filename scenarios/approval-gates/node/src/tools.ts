export interface ToolResult {
  output: string;
}

const BALANCES: Record<string, number> = {
  "acc-001": 12450,
  "acc-002": 3200,
  "acc-003": 875.5,
};

export function getBalance(accountId: string): ToolResult {
  const balance = BALANCES[accountId] ?? 0;
  return { output: `$${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}` };
}

export function transferFunds(fromAccount: string, toAccount: string, amount: number): ToolResult {
  return { output: `Transferred $${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })} from ${fromAccount} to ${toAccount}` };
}
