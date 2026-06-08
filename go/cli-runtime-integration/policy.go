package main

import (
	"context"

	"github.com/ai-agent-assembly/go-sdk/assembly"
)

// mockClient is an offline GovernanceClient that always allows every tool call.
// Replace this with a transport-backed client to connect to a real sidecar or gateway.
type mockClient struct{}

func (m *mockClient) Check(_ context.Context, _ assembly.CheckRequest) (assembly.Decision, error) {
	return assembly.Decision{Denied: false, Reason: "allowed by offline mock"}, nil
}

func (m *mockClient) WaitForApproval(_ context.Context, _ assembly.ApprovalRequest) (assembly.Decision, error) {
	return assembly.Decision{Denied: false}, nil
}

func (m *mockClient) RecordResult(_ context.Context, _ assembly.RecordRequest) error { return nil }
func (m *mockClient) Close() error                                                    { return nil }
