# Govern the concrete demo tool class BEFORE init_assembly so the offline
# LocalPolicyEngine stays wired as the interceptor (the patch is idempotent).
govern_tool_class(DemoTool, LocalPolicyEngine())

try:
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="google-adk-demo-agent",
        mode="sdk-only",
        # No gateway here: the default posture fails closed when registration
        # can't reach one, so an offline demo must name its dry-run posture.
        enforcement_mode="observe",
    ) as ctx:
