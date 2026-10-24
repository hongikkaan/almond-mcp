# Shared native Engine

Follow `../../../AGENTS.md`. Own native transport completion, connection identity
and shared storage leases. Depend on platform/Rhino APIs, never on either host.
Both Bridge and COS consume this assembly. Keep their shipped DLLs identical
after an Engine change and run the local native fixtures plus host integrations.
Do not add Python MCP or COS adapter policy here.
