package main

import (
	"context"
	"errors"
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
	ctx := assembly.WithAgentID(context.Background(), "cli-runtime-demo")

	// Attempt to start the aasm sidecar. This shows the CLI runtime integration
	// path — the sidecar runs alongside the Go process and intercepts governance calls.
	sidecarRunning := startSidecar()

	// Build the governance client. When the sidecar is running, production apps
	// would point a real transport at the sidecar endpoint. This example uses
	// the offline mock to remain runnable in CI without a live gateway.
	client := buildGovernanceClient(sidecarRunning)
	defer client.Close()

	tools := assembly.WrapTools([]assembly.Tool{&echoTool{}}, client)

	input := "Hello from the CLI runtime!"
	fmt.Printf("[assembly] governance: ALLOWED  tool=echo input=%q\n", input)

	result, err := tools[0].Call(ctx, input)
	if err != nil {
		log.Fatalf("[assembly] tool call failed: %v", err)
	}
	fmt.Printf("[assembly] tool result: %s\n", result)
}

// startSidecar calls assembly.InitAssembly to probe for and optionally start
// the aasm sidecar. Returns true when the sidecar is reachable.
func startSidecar() bool {
	fmt.Println("[runtime] probing for aasm sidecar...")

	err := assembly.InitAssembly("cli-runtime-demo")
	if err != nil {
		if errors.Is(err, assembly.ErrBinaryNotFound) {
			fmt.Println("[runtime] aasm binary not found — continuing in offline fallback mode")
			fmt.Println("[runtime] install aasm: brew install ai-agent-assembly/tap/aasm")
			return false
		}
		log.Printf("[runtime] sidecar init warning: %v", err)
		return false
	}

	fmt.Printf("[runtime] sidecar ready at %s:%d\n", assembly.DefaultRuntimeHost, assembly.DefaultPort)
	return true
}

// buildGovernanceClient returns the governance client to use for tool wrapping.
// This example always uses the offline mock; replace with a gateway-backed
// implementation in production.
func buildGovernanceClient(sidecarRunning bool) assembly.GovernanceClient {
	if sidecarRunning {
		fmt.Printf("[runtime] sidecar is running — governance calls will reach %s:%d\n",
			assembly.DefaultRuntimeHost, assembly.DefaultPort)
		fmt.Println("[runtime] using offline mock client for this example (swap for real transport in production)")
	} else {
		fmt.Println("[runtime] using offline mock governance client")
	}
	return &mockClient{}
}
