export interface OpenAITool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, { type: string; description: string }>;
      required: string[];
    };
  };
}

export interface ToolResult {
  output: string;
  allowed: boolean;
}

export const TOOL_DEFINITIONS: OpenAITool[] = [
  {
    type: "function",
    function: {
      name: "search_web",
      description: "Search the web for information.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
        },
        required: ["query"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "send_email",
      description: "Send an email to a recipient.",
      parameters: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email address" },
          subject: { type: "string", description: "Email subject" },
          body: { type: "string", description: "Email body" },
        },
        required: ["to", "subject", "body"],
      },
    },
  },
];

export function searchWeb(query: string): ToolResult {
  return {
    output: `Search results for "${query}": [mock result 1] [mock result 2]`,
    allowed: true,
  };
}

export function sendEmail(to: string, subject: string): ToolResult {
  return {
    output: `[BLOCKED] sendEmail(to="${to}", subject="${subject}") denied by policy.`,
    allowed: false,
  };
}
