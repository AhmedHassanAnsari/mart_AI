Prompt 14 — test what's testable now

Test the workflow trigger and Inventory agent invocation end-to-end up to (but not through) the get_reorder_context call — confirm the wake event reaches the agent correctly, and that the expected failure at the context-service call is the only failure point. Don't attempt to mock context-service's response just to get a decision out — that would hide whether the contract itself is well-formed. Show me the failure point clearly.

Build context-service as its own small FastAPI-based MCP server, exposing exactly one tool: get_reorder_context(tenant_id, item_id), matching the contract we defined in Prompt 12. For now, have it return a hardcoded stub response matching that contract's shape — don't wire in KSOR or Postgres yet. Confirm the tool registers correctly and is discoverable when a test MCP client connects to it.

Prompt 16 — wire in the Postgres side

Implement the Postgres portion of get_reorder_context: given tenant_id, resolve the correct schema (via the tenants table), then run a fixed, parameterized read-only query against that schema's inventory and orders tables to get current quantity_on_hand, reorder_point, and any pending orders for item_id. Use a database role with read-only, schema-scoped permissions — ask me for the connection details/role rather than assuming what's already configured. Leave the sales-velocity calculation and KSOR parts as stubs for now.

Prompt 17 — wire in the KSOR side

Implement the KSOR portion: context-service should act as an MCP client, calling the live KSOR server at http://localhost:8080/mcp to fetch the relevant policy (reorder rules, blast-radius thresholds) for this tenant_id/item_id. Show me the actual query/prompt you send to KSOR before finalizing it, since the phrasing affects what KSOR returns.

Prompt 18 — merge and return real data

Combine the Postgres facts and KSOR policy into the single merged response get_reorder_context returns, replacing the earlier stub. Test it against the seeded "Lalkurti Electronics" data — call the tool directly (not through the agent yet) and show me the full output for one real item.

Prompt 19 — connect the Inventory agent for real

Now point the Inventory agent (from Prompt 12) at the real context-service instead of the expected-to-fail call. Re-run the Prompt 14 end-to-end test: sell enough Coolers to cross the reorder point, confirm the trigger fires, the workflow wakes the agent, the agent successfully calls context-service, and produces an actual ordering decision based on real data. Show me the full trace.