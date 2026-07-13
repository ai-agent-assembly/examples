// Command langchaingo shows how to govern a LangChainGo agent's tool calls with
// Agent Assembly. LangChainGo tools (github.com/tmc/langchaingo/tools.Tool) are
// wrapped by assembly.WrapTools, so every tool the LLM decides to call is first
// checked against a governance policy. A fake LLM stands in for a real model,
// so the example builds, runs, and tests with no API keys and no network.
package main

import (
	"context"
	"errors"
	"fmt"
	"log"

	"github.com/ai-agent-assembly/go-sdk/assembly"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/fake"
)

func main() {
	// Tag the context so governance records carry this agent's ID.
	ctx := assembly.WithAgentID(context.Background(), "langchaingo-demo")

	fmt.Println("[assembly] governing LangChainGo tools via an offline policy client")
	fmt.Printf("[policy] loaded: search=ALLOW, send-email=DENY\n\n")

	// A fake LLM keeps the example offline. In production this is an
	// openai.New(), anthropic.New(), etc. We use it to show the agent's
	// "reasoning" step runs through LangChainGo before any tool is called.
	model := fake.NewFakeLLM([]string{
		"I should search for the topic, then email the result.",
	})
	plan, err := llms.GenerateFromSinglePrompt(ctx, model, "How do I summarize a topic and notify the user?")
	if err != nil {
		log.Fatalf("[llm] generation failed: %v", err)
	}
	fmt.Printf("[llm] plan: %s\n\n", plan)

	// region: quickstart
	// Wrap the LangChainGo tools with Agent Assembly governance. The wrapped
	// values still satisfy langchaingo's tools.Tool, so they can be handed
	// straight to a LangChainGo agent/executor.
	governed := assembly.WrapTools(
		[]assembly.Tool{&searchTool{}, &sendEmailTool{}},
		&policyClient{},
	)
	// endregion

	// The agent attempts both tool calls from its plan. Governance allows the
	// safe one and blocks the side-effecting one.
	runTool(ctx, governed[0], "agent governance")
	fmt.Println()
	runTool(ctx, governed[1], "user@example.com")
}

func runTool(ctx context.Context, tool assembly.Tool, input string) {
	fmt.Printf("[agent] calling tool: %s  input=%q\n", tool.Name(), input)

	result, err := tool.Call(ctx, input)
	if err != nil {
		var pve *assembly.PolicyViolationError
		if errors.As(err, &pve) {
			fmt.Printf("[agent] blocked: %v\n", pve)
			return
		}
		fmt.Printf("[agent] unexpected error: %v\n", err)
		return
	}
	fmt.Printf("[agent] result: %s\n", result)
}
