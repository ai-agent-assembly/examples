adapter = PydanticAIAdapter()
adapter.set_process_agent_id("pydantic-ai-demo-agent")
adapter.register_hooks(LocalPolicyEngine())

try:
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="pydantic-ai-demo-agent",
        mode="sdk-only",
        # No gateway here: the default posture fails closed when registration
        # can't reach one, so an offline demo must name its dry-run posture.
        enforcement_mode="observe",
    ) as ctx:
