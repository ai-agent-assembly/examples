policy = LocalPolicyEngine()
patch = SmolagentsPatch(policy)
patch.apply()

print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

with init_assembly(
    gateway_url=gateway_url,
    api_key=api_key,
    agent_id="smolagents-demo-agent",
    mode="sdk-only",
    # No gateway here, so the offline demo runs in observe, the dry-run posture:
    # every action proceeds, the SDK's local checks fail open, and a gateway
    # would only record what it would have blocked.
    enforcement_mode="observe",
) as ctx:
