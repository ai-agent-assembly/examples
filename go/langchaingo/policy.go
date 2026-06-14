package main

import (
	"context"
	"fmt"

	"github.com/ai-agent-assembly/go-sdk/assembly"
)

// blockedTools lists tool names this policy client denies. Everything else
// is allowed. In production, swap this for a client backed by a real gateway.
var blockedTools = map[string]string{
	"send-email": "outbound email is blocked by policy",
}

// policyClient enforces per-tool allow/deny rules in-process. It implements
// assembly.GovernanceClient and requires no live gateway, so the example
// builds and tests fully offline.
type policyClient struct{}

func (p *policyClient) Check(_ context.Context, req assembly.CheckRequest) (assembly.Decision, error) {
	if reason, blocked := blockedTools[req.ToolName]; blocked {
		fmt.Printf("[policy] DENIED   tool=%s  reason=%q\n", req.ToolName, reason)
		return assembly.Decision{Denied: true, Reason: reason}, nil
	}
	fmt.Printf("[policy] ALLOWED  tool=%s\n", req.ToolName)
	return assembly.Decision{Denied: false}, nil
}

func (p *policyClient) WaitForApproval(_ context.Context, _ assembly.ApprovalRequest) (assembly.Decision, error) {
	return assembly.Decision{Denied: false}, nil
}

func (p *policyClient) RecordResult(_ context.Context, _ assembly.RecordRequest) error { return nil }
func (p *policyClient) Close() error                                                   { return nil }
