# Govern the concrete demo tool class BEFORE init_assembly so the offline
# LocalPolicyEngine stays wired as the interceptor (the patch is idempotent).
govern_tool_class(DemoTool, LocalPolicyEngine())

try:
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="google-adk-demo-agent",
        mode="sdk-only",
        # No gateway here, so the offline demo runs in observe, the dry-run posture:
        # every action proceeds, the SDK's local checks fail open, and a gateway
        # would only record what it would have blocked.
        enforcement_mode="observe",
    ) as ctx:
