package main

import (
	"context"

	"github.com/tmc/langchaingo/tools"
)

// The tools below implement langchaingo's tools.Tool interface
// (Name, Description, Call). That interface is structurally identical to
// assembly.Tool, so each tool can be handed to a LangChainGo agent AND
// wrapped by assembly.WrapTools for governance without any adapter.

// searchTool simulates a read-only knowledge lookup — a safe operation.
type searchTool struct{}

func (s *searchTool) Name() string        { return "search" }
func (s *searchTool) Description() string { return "Looks up a topic and returns a short summary." }
func (s *searchTool) Call(_ context.Context, query string) (string, error) {
	return "(summary for " + query + ")", nil
}

// sendEmailTool simulates sending an email — a side-effecting operation
// that this example's policy blocks.
type sendEmailTool struct{}

func (e *sendEmailTool) Name() string        { return "send-email" }
func (e *sendEmailTool) Description() string { return "Sends an email to the given recipient." }
func (e *sendEmailTool) Call(_ context.Context, recipient string) (string, error) {
	return "sent email to " + recipient, nil
}

// Compile-time proof that both tools satisfy langchaingo's tools.Tool.
var (
	_ tools.Tool = (*searchTool)(nil)
	_ tools.Tool = (*sendEmailTool)(nil)
)
