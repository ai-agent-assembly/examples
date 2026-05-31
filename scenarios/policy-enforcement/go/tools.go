package main

import (
	"context"
	"fmt"
	"strings"
)

// readConfigTool returns a configuration value (safe — ALLOWED).
type readConfigTool struct{}

func (t *readConfigTool) Name() string        { return "read_config" }
func (t *readConfigTool) Description() string { return "Read a configuration value by key" }
func (t *readConfigTool) Call(_ context.Context, input string) (string, error) {
	config := map[string]string{
		"database.host": "localhost:5432",
		"service.port":  "8080",
		"log.level":     "INFO",
	}
	if val, ok := config[input]; ok {
		return val, nil
	}
	return fmt.Sprintf("(no value for '%s')", input), nil
}

// listAgentsTool returns registered agent IDs (safe — ALLOWED).
type listAgentsTool struct{}

func (t *listAgentsTool) Name() string        { return "list_agents" }
func (t *listAgentsTool) Description() string { return "List registered agent IDs" }
func (t *listAgentsTool) Call(_ context.Context, _ string) (string, error) {
	return strings.Join([]string{"agent-001", "agent-002", "agent-003"}, ", "), nil
}

// deleteAgentTool removes an agent (RISKY — DENIED by policy).
type deleteAgentTool struct{}

func (t *deleteAgentTool) Name() string        { return "delete_agent" }
func (t *deleteAgentTool) Description() string { return "Delete an agent from the registry" }
func (t *deleteAgentTool) Call(_ context.Context, input string) (string, error) {
	return fmt.Sprintf("Deleted agent %s", input), nil
}

// sendEmailTool sends email (RISKY — DENIED by policy: network egress).
type sendEmailTool struct{}

func (t *sendEmailTool) Name() string        { return "send_email" }
func (t *sendEmailTool) Description() string { return "Send an email to an external address" }
func (t *sendEmailTool) Call(_ context.Context, input string) (string, error) {
	return fmt.Sprintf("Email sent: %s", input), nil
}
