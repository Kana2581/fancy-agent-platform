# Filesystem Skill Runtime

Fancy Agent treats Skill packages as filesystem data rather than database rows.
Every valid package is a directory containing a `SKILL.md` with YAML frontmatter
fields `name` and `description`.

## Storage

- System packages live under `SYSTEM_SKILLS_DIR` and are mounted read-only.
- User packages live under `USER_SKILLS_DIR/<user_id>/<skill-name>` on the persistent
  `skill_packages` volume. The directory name is the trimmed original Skill name.
- MySQL does not store Skill content, metadata, files, or Agent bindings.
- The backend scans the package directories on demand. Invalid packages remain
  on disk but are excluded from the model's available Skill list.

## Runtime

When an Agent is built for a session, one filesystem scan provides both the
system prompt metadata and the sandbox mount context. The model sees paths such
as `/skills/system/skill-creator` and `/skills/user/report-writer` and uses the
`sandbox` tool with a single `command` argument to read
`SKILL.md`, inspect resources, and run scripts.

The sandbox mounts:

- `/workspace` for the current session's files;
- `/skills/system` as read-only;
- `/skills/user` for the current user as writable.

Each catalog entry includes an exact `mount_path` such as
`/skills/user/hello-trilingual`; models must use that path verbatim.

After a Bash execution, changed Skill paths are returned by the sandbox and the
backend rescans affected packages before returning the tool result. A newly
created valid package is therefore available on the next model call without a
restart. A package that fails frontmatter, path, or size validation is reported
as `invalid` and is not injected into the prompt.

## API and UI

`GET /api/v1/skills` lists the current filesystem catalog. The tree and file
endpoints expose package structure and text previews without permitting edits.
Skill changes are made by the model through Bash; system packages remain
read-only.

## Migration

Existing database-backed packages must be materialized before applying
`backend/db_init/02_remove_legacy_skill_tables.sql`:

```bash
cd backend
uv run python scripts/migrate_legacy_skills_to_files.py
```

The migration script must run before the SQL file and after backing up the
database and user Skill volume.
