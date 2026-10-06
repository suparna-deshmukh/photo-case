# D0 - Tool inventory (TP1)
Session date: 2026-10-06 (agent: Codex CLI on macOS)

## shell/process
- exec_command - run a shell command in a PTY; returns output or a session ID for ongoing interaction.
- write_stdin - write input to / poll a running exec session (used for long jobs).

## filesystem
- No dedicated filesystem tool. All file ops (create/read/write/delete) are done via shell commands (cat, rg, find, mkdir, rm). No apply_patch tool in this session.

## browser
- NONE. The user's Codex config contains browser/computer-use plugins for the ChatGPT app, but no browser tool is exposed to this agent session.
- Consequence: keys gate (AI Studio / Pexels / Hugging Face) falls back to HUMAN GATE with click-paths; AI Studio pricing page (sign-in-walled) could not be verified by script.

## Google Workspace (Docs/Sheets/Forms/Drive/Slides)
- NONE. No gws/gdoc tools or MCP server for Google Workspace in this session.
- Consequence: pre-registered hypotheses doc falls back to research/hypotheses_preregistered.md (SHA-256 recorded in STATE) + HUMAN GATE for the user to create/share the Google Doc before D6.

## Hugging Face
- No dedicated tool. huggingface_hub library + HF REST API via shell will be used after D0 step 5 install.

## other
- view_image - view a local image file (used for visual QA of figures/screenshots).
- list_mcp_resources / read_mcp_resource - list/read MCP server resources. Present servers: codex_apps (work-pets, plugin-management - not relevant), notion (documentation resources only; no callable Notion tools in this session).
- get_goal / create_goal / update_goal - goal tracking (not needed for D0).
- request_user_input - plan-mode only, not available in this run.

## MCP servers configured on the machine (context, not callable from this session)
- node_repl (ChatGPT app CUA runtime, browser backends chrome/iab), notion (mcp.notion.com), metabase (mcp URL), github (npx server, disabled in this session), computer-use (enabled=false).
