# Agent Instructions

This repository contains assorted personal automation and utility files.

## General

- Keep changes small and scoped to the requested file or tool.
- Do not reformat unrelated files.
- Preserve existing user changes and do not reset or revert work unless explicitly asked.
- Prefer `rg` for searching.
- Use existing style and naming conventions in each directory.

## Home Assistant

- Treat files under `homeassistant/` as Home Assistant YAML.
- Keep indentation valid and avoid broad rewrites from UI-exported YAML.
- For AWTRIX scripts, preserve existing `topicname`, `duration`, `textcase`, and delete-app behavior unless the task explicitly asks to change them.
- Prefer Jinja templates that handle unknown or unavailable sensor states gracefully.

## Verification

- After YAML edits, inspect the changed block and run a lightweight syntax check when a suitable local tool is available.
- If a change cannot be validated locally, say so in the final response.
