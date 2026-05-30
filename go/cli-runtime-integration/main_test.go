package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/AI-agent-assembly/go-sdk/assembly"
)

func TestEchoToolReturnsInput(t *testing.T) {
	t.Parallel()

	result, err := (&echoTool{}).Call(context.Background(), "cli-test")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "cli-test" {
		t.Fatalf("expected %q, got %q", "cli-test", result)
	}
}

func TestStartSidecarReturnsFalseWhenBinaryAbsent(t *testing.T) {
	// Override PATH to an empty temp dir so aasm is not found.
	dir := t.TempDir()
	t.Setenv("PATH", dir)
	t.Setenv("HOME", filepath.Join(dir, "no-home"))

	running := startSidecar()
	if running {
		t.Fatal("expected startSidecar to return false when aasm binary is absent")
	}
}

func TestMockClientAllowsToolCall(t *testing.T) {
	t.Parallel()

	client := &mockClient{}
	tools := assembly.WrapTools([]assembly.Tool{&echoTool{}}, client)

	result, err := tools[0].Call(context.Background(), "hello")
	if err != nil {
		t.Fatalf("expected allowed call, got error: %v", err)
	}
	if result != "hello" {
		t.Fatalf("expected %q, got %q", "hello", result)
	}
}

func TestBuildGovernanceClientReturnsMock(t *testing.T) {
	t.Parallel()

	for _, sidecarRunning := range []bool{true, false} {
		client := buildGovernanceClient(sidecarRunning)
		if client == nil {
			t.Fatalf("buildGovernanceClient(%v) returned nil", sidecarRunning)
		}
		client.Close()
	}
}

func TestInitAssemblyReturnsBinaryNotFoundInEmptyPath(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("PATH", dir)
	t.Setenv("HOME", filepath.Join(dir, "no-home"))

	// Ensure the docker fallback path doesn't exist either.
	_ = os.Remove(filepath.Join(dir, "aasm"))

	err := assembly.InitAssembly("test-agent")
	if err == nil {
		t.Fatal("expected ErrBinaryNotFound when aasm is absent")
	}
	if !errors.Is(err, assembly.ErrBinaryNotFound) {
		t.Fatalf("expected ErrBinaryNotFound, got %T: %v", err, err)
	}
}
