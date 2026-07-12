// Live registration smoke — Go SDK — Agent Assembly examples.
//
// Unlike go/basic-agent and go/tool-policy (which wrap tools with an offline
// mockClient and never call assembly.Init), this driver exercises the REAL
// transport: assembly.Init boots/reaches a running gateway and registers this
// agent over gRPC, exactly as a production integration does. There is no mock
// client here by design — that is the whole point of the verify-live lane
// (AAASM-4475): prove the native/gRPC registration path actually works.
//
// The verify-live workflow starts a real `aasm start --mode local` gateway,
// runs this driver against it, then asserts this agent appears in the
// gateway's /api/v1/agents REST surface. The driver itself only has to init,
// register, and run one governed call; the workflow owns the visibility check.
//
// Env:
//   AA_GATEWAY_URL  gateway endpoint the SDK registers against (gRPC :50051).
//   AA_AGENT_ID     the id to register under (must match the workflow's assert).
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/ai-agent-assembly/go-sdk/assembly"
)

// readFileTool is a trivial governed tool. Its body never runs unless the
// gateway allows the call — the governance check happens in the wrapped Call.
type readFileTool struct{}

func (t *readFileTool) Name() string        { return "read_file" }
func (t *readFileTool) Description() string { return "Reads a file path (governed)." }
func (t *readFileTool) Call(_ context.Context, input string) (string, error) {
	return "read ok: " + input, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	agentID := getenv("AA_AGENT_ID", "live-smoke-go")
	gatewayURL := getenv("AA_GATEWAY_URL", "http://127.0.0.1:50051")

	ctx := context.Background()

	// Init registers the agent with the real gateway (no mock). If the gateway
	// is unreachable — or the SDK's registration transport is broken (the class
	// of bug AAASM-4469 found) — this returns an error and the driver exits
	// non-zero, which is exactly the signal verify-live exists to surface.
	a, err := assembly.Init(ctx,
		assembly.WithGatewayURL(gatewayURL),
		assembly.WithSelfAgentID(agentID),
	)
	if err != nil {
		log.Fatalf("[live] assembly.Init failed to register %q against %s: %v", agentID, gatewayURL, err)
	}
	defer func() { _ = a.Close() }()

	fmt.Printf("[live] registered agent %q against %s\n", agentID, gatewayURL)

	// One governed call over the real transport. a.WrapTools routes the check
	// through the gateway established by Init (not an in-process mock).
	tools := a.WrapTools([]assembly.Tool{&readFileTool{}})
	out, err := tools[0].Call(ctx, `{"path":"/data/report.csv"}`)
	if err != nil {
		log.Fatalf("[live] governed read_file call failed: %v", err)
	}
	fmt.Printf("[live] governed read_file result: %s\n", out)
}
