package main

import (
	"context"
	"fmt"
	"log"

	"github.com/ai-agent-assembly/go-sdk/assembly"
)

// echoTool satisfies assembly.Tool and returns its input unchanged.
type echoTool struct{}

func (e *echoTool) Name() string        { return "echo" }
func (e *echoTool) Description() string { return "Returns its input string unchanged." }
func (e *echoTool) Call(_ context.Context, input string) (string, error) {
	return input, nil
}

func main() {
	// Tag the context so governance records include this agent's ID.
	ctx := assembly.WithAgentID(context.Background(), "basic-agent-demo")

	// Use the offline mock governance client.
	// In production, replace mockClient with a client backed by a real gateway.
	fmt.Println("[assembly] using offline mock governance client")
	client := &mockClient{}

	// Wrap the tool — every Call now goes through the governance client first.
	tools := assembly.WrapTools([]assembly.Tool{&echoTool{}}, client)

	input := "Hello, Agent Assembly!"
	fmt.Printf("[assembly] governance: ALLOWED  tool=echo input=%q\n", input)

	result, err := tools[0].Call(ctx, input)
	if err != nil {
		log.Fatalf("[assembly] tool call failed: %v", err)
	}
	fmt.Printf("[assembly] tool result: %s\n", result)
}
