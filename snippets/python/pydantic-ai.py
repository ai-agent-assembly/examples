adapter = PydanticAIAdapter()
adapter.set_process_agent_id("pydantic-ai-demo-agent")
adapter.register_hooks(LocalPolicyEngine())

try:
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="pydantic-ai-demo-agent",
        mode="sdk-only",
        # No gateway here, so the offline demo runs in observe, the dry-run posture:
        # every action proceeds, the SDK's local checks fail open, and a gateway
        # would only record what it would have blocked.
        enforcement_mode="observe",
    ) as ctx:
