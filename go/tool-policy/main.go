package main

import (
	"context"
	"errors"
	"fmt"

	"github.com/AI-agent-assembly/go-sdk/assembly"
)

func main() {
	ctx := assembly.WithAgentID(context.Background(), "tool-policy-demo")

	fmt.Printf("[policy] client loaded: read-file=ALLOW, delete-file=DENY\n\n")

	client := &policyClient{}
	tools := assembly.WrapTools(
		[]assembly.Tool{&readFileTool{}, &deleteFileTool{}},
		client,
	)

	runTool(ctx, tools[0], "config.yaml")
	fmt.Println()
	runTool(ctx, tools[1], "config.yaml")
}

func runTool(ctx context.Context, tool assembly.Tool, input string) {
	fmt.Printf("[tool] calling: %s  input=%q\n", tool.Name(), input)

	result, err := tool.Call(ctx, input)
	if err != nil {
		var pve *assembly.PolicyViolationError
		if errors.As(err, &pve) {
			fmt.Printf("[tool] error: %v\n", pve)
			return
		}
		fmt.Printf("[tool] unexpected error: %v\n", err)
		return
	}
	fmt.Printf("[tool] result: %s\n", result)
}
