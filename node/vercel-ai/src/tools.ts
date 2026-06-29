import { tool, type Tool } from "ai";
import { z } from "zod";

type EmptyContext = Record<string, never>;

/**
 * Tools defined with the Vercel AI SDK `tool()` factory.
 *
 * Each tool returns mock output so the example runs fully offline — no provider
 * key and no live LLM are required. `withAssembly` (in index.ts) wraps each
 * tool's `execute` to enforce the local policy before it runs.
 */
export const getWeatherTool: Tool<{ location: string }, string, EmptyContext> = tool({
  description: "Look up the current weather for a location.",
  inputSchema: z.object({ location: z.string() }),
  execute: async ({ location }: { location: string }): Promise<string> =>
    `Weather in ${location}: 22°C, partly cloudy. [mock]`,
});

export const sendEmailTool: Tool<{ to: string; body: string }, string, EmptyContext> = tool({
  description: "Send an email to a recipient.",
  inputSchema: z.object({ to: z.string(), body: z.string() }),
  execute: async ({ to, body }: { to: string; body: string }): Promise<string> =>
    `Email sent to ${to}: "${body.slice(0, 40)}" [mock]`,
});
