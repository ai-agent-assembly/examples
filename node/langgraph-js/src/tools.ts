export interface ToolResult {
  output: string;
  allowed: boolean;
}

export function searchDocs(query: string): ToolResult {
  return {
    output: `Top result for "${query}": Agent Assembly governs every tool call. [mock]`,
    allowed: true,
  };
}

export function executeShell(command: string): ToolResult {
  return {
    output: `[BLOCKED] executeShell("${command}") denied by policy.`,
    allowed: false,
  };
}

export const TOOLS = {
  search_docs: (args: Record<string, unknown>): ToolResult =>
    searchDocs(typeof args["query"] === "string" ? args["query"] : ""),
  execute_shell: (args: Record<string, unknown>): ToolResult =>
    executeShell(typeof args["command"] === "string" ? args["command"] : ""),
} as const;

export type ToolName = keyof typeof TOOLS;
