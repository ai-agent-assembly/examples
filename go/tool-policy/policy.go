package main

import (
	"context"
	"fmt"

	"github.com/ai-agent-assembly/go-sdk/assembly"
)

// blockedTools lists tool names that this policy client will deny.
var blockedTools = map[string]string{
	"delete-file": "delete operations are blocked by policy",
}

// policyClient enforces per-tool allow/deny rules in-process.
// It implements assembly.GovernanceClient and requires no live gateway.
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
func (p *policyClient) Close() error                                                    { return nil }
