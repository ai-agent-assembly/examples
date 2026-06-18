export interface ToolResult {
  output: string;
  allowed: boolean;
}

export function getWeather(location: string): ToolResult {
  return {
    output: `Weather in ${location}: 22°C, partly cloudy. [mock]`,
    allowed: true,
  };
}

export function deleteFile(path: string): ToolResult {
  return {
    output: `[BLOCKED] deleteFile("${path}") denied by policy.`,
    allowed: false,
  };
}

export const TOOLS = {
  get_weather: (args: Record<string, unknown>): ToolResult =>
    getWeather(typeof args["location"] === "string" ? args["location"] : "unknown"),
  delete_file: (args: Record<string, unknown>): ToolResult =>
    deleteFile(typeof args["path"] === "string" ? args["path"] : ""),
} as const;

export type ToolName = keyof typeof TOOLS;
