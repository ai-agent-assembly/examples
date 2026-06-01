export interface ToolResult {
  output: string;
}

const BALANCES: Record<string, number> = {
  "acc-001": 12450.00,
  "acc-002": 3200.00,
  "acc-003": 875.50,
};

export function getBalance(accountId: string): ToolResult {
  const balance = BALANCES[accountId] ?? 0;
  return { output: `$${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}` };
}

export function transferFunds(fromAccount: string, toAccount: string, amount: number): ToolResult {
  return { output: `Transferred $${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })} from ${fromAccount} to ${toAccount}` };
}
