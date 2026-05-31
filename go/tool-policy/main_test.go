package main

import (
	"context"
	"errors"
	"testing"

	"github.com/AI-agent-assembly/go-sdk/assembly"
)

func TestReadFileToolReturnsContents(t *testing.T) {
	t.Parallel()

	result, err := (&readFileTool{}).Call(context.Background(), "test.yaml")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "(contents of test.yaml)" {
		t.Fatalf("unexpected result: %q", result)
	}
}

func TestDeleteFileToolReturnsDeleted(t *testing.T) {
	t.Parallel()

	result, err := (&deleteFileTool{}).Call(context.Background(), "old.yaml")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "deleted old.yaml" {
		t.Fatalf("unexpected result: %q", result)
	}
}

func TestPolicyClientAllowsReadFile(t *testing.T) {
	t.Parallel()

	client := &policyClient{}
	tools := assembly.WrapTools([]assembly.Tool{&readFileTool{}}, client)

	result, err := tools[0].Call(context.Background(), "allowed.yaml")
	if err != nil {
		t.Fatalf("expected allowed call, got error: %v", err)
	}
	if result != "(contents of allowed.yaml)" {
		t.Fatalf("unexpected result: %q", result)
	}
}

func TestPolicyClientDeniesDeleteFile(t *testing.T) {
	t.Parallel()

	client := &policyClient{}
	tools := assembly.WrapTools([]assembly.Tool{&deleteFileTool{}}, client)

	_, err := tools[0].Call(context.Background(), "blocked.yaml")
	if err == nil {
		t.Fatal("expected denied call to return error")
	}

	var pve *assembly.PolicyViolationError
	if !errors.As(err, &pve) {
		t.Fatalf("expected PolicyViolationError, got %T: %v", err, err)
	}
	if pve.ToolName != "delete-file" {
		t.Fatalf("expected ToolName %q, got %q", "delete-file", pve.ToolName)
	}
	if pve.Reason != "delete operations are blocked by policy" {
		t.Fatalf("unexpected denial reason: %q", pve.Reason)
	}
}

func TestAllBlockedToolsAreDenied(t *testing.T) {
	t.Parallel()

	client := &policyClient{}
	for toolName, expectedReason := range blockedTools {
		toolName, expectedReason := toolName, expectedReason

		stubTool := &namedTool{name: toolName}
		wrapped := assembly.WrapTools([]assembly.Tool{stubTool}, client)

		_, err := wrapped[0].Call(context.Background(), "input")
		var pve *assembly.PolicyViolationError
		if !errors.As(err, &pve) {
			t.Errorf("tool %q: expected PolicyViolationError, got %T", toolName, err)
			continue
		}
		if pve.Reason != expectedReason {
			t.Errorf("tool %q: expected reason %q, got %q", toolName, expectedReason, pve.Reason)
		}
	}
}

// namedTool is a stub that always returns "ok" when called.
type namedTool struct{ name string }

func (n *namedTool) Name() string                                     { return n.name }
func (n *namedTool) Description() string                              { return "stub" }
func (n *namedTool) Call(_ context.Context, _ string) (string, error) { return "ok", nil }
