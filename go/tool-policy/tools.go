package main

import "context"

// readFileTool simulates reading a file — a safe, read-only operation.
type readFileTool struct{}

func (r *readFileTool) Name() string        { return "read-file" }
func (r *readFileTool) Description() string { return "Reads a file and returns its contents." }
func (r *readFileTool) Call(_ context.Context, path string) (string, error) {
	return "(contents of " + path + ")", nil
}

// deleteFileTool simulates deleting a file — a destructive operation.
type deleteFileTool struct{}

func (d *deleteFileTool) Name() string        { return "delete-file" }
func (d *deleteFileTool) Description() string { return "Deletes a file permanently." }
func (d *deleteFileTool) Call(_ context.Context, path string) (string, error) {
	return "deleted " + path, nil
}
