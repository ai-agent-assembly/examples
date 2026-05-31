export interface ToolResult {
  output: string;
  allowed: boolean;
}

export function readFile(path: string): ToolResult {
  return {
    output: `Contents of "${path}": [mock file contents line 1, line 2]`,
    allowed: true,
  };
}

export function writeFile(path: string, content: string): ToolResult {
  return {
    output: `[BLOCKED] writeFile("${path}", "${content.slice(0, 20)}...") denied by policy.`,
    allowed: false,
  };
}
