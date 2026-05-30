package main

import (
	"context"
	"errors"
	"testing"

	"github.com/AI-agent-assembly/go-sdk/assembly"
)

func TestEchoToolReturnsInput(t *testing.T) {
	t.Parallel()

	tool := &echoTool{}
	result, err := tool.Call(context.Background(), "hello")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "hello" {
		t.Fatalf("expected %q, got %q", "hello", result)
	}
}

func TestEchoToolName(t *testing.T) {
	t.Parallel()

	if (&echoTool{}).Name() != "echo" {
		t.Fatal("expected tool name to be echo")
	}
}

func TestWrappedToolAllowedByMock(t *testing.T) {
	t.Parallel()

	client := &mockClient{}
	tools := assembly.WrapTools([]assembly.Tool{&echoTool{}}, client)

	ctx := assembly.WithAgentID(context.Background(), "test-agent")
	result, err := tools[0].Call(ctx, "ping")
	if err != nil {
		t.Fatalf("expected allowed call, got error: %v", err)
	}
	if result != "ping" {
		t.Fatalf("expected %q, got %q", "ping", result)
	}
}

func TestWrappedToolDeniedByClient(t *testing.T) {
	t.Parallel()

	client := &denyClient{reason: "test-deny"}
	tools := assembly.WrapTools([]assembly.Tool{&echoTool{}}, client)

	_, err := tools[0].Call(context.Background(), "blocked")
	if err == nil {
		t.Fatal("expected denied call to return error")
	}

	var pve *assembly.PolicyViolationError
	if !errors.As(err, &pve) {
		t.Fatalf("expected PolicyViolationError, got %T: %v", err, err)
	}
	if pve.Reason != "test-deny" {
		t.Fatalf("expected reason %q, got %q", "test-deny", pve.Reason)
	}
}

// denyClient is a GovernanceClient that denies every tool call.
type denyClient struct{ reason string }

func (d *denyClient) Check(_ context.Context, _ assembly.CheckRequest) (assembly.Decision, error) {
	return assembly.Decision{Denied: true, Reason: d.reason}, nil
}

func (d *denyClient) WaitForApproval(_ context.Context, _ assembly.ApprovalRequest) (assembly.Decision, error) {
	return assembly.Decision{Denied: true, Reason: d.reason}, nil
}

func (d *denyClient) RecordResult(_ context.Context, _ assembly.RecordRequest) error { return nil }
func (d *denyClient) Close() error                                                    { return nil }
