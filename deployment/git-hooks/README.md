# Git hooks

Tracked git hooks for this repo. They are **not** active until each clone points
git at this directory (git can't enable hooks automatically, for security).

## One-time setup (per clone)

```bash
git config core.hooksPath deployment/git-hooks
```

Every hook in the folder is now live for that clone. Undo it with
`git config --unset core.hooksPath`.

## Hooks

### `post-checkout`
After a **branch switch**, it re-syncs the running `copo_web` container to the
checked-out code:

- If anything under `requirements/` differs between the branch the developer
  left and the one that was switched to, it runs 
  `pip install -r requirements/dev.txt` in the container.
- If the schema, profile type or Django group definitions differ, it re-runs the
  Django commands - `setup_schemas`, `setup_profile_types` and `setup_groups`
  respectively which resyncs both MongoDB and PostgreSQL databases.

COPO feeds these definitions into the database once and then serves them from
there, so switching between branches that differ
(e.g. `main` branch <-> `edp` branch) would otherwise leave the database
describing the old branch (import errors, profiles that won't render).
The hook keeps the database in step with the code.

- Runs only on real branch switches and only when relevant files have been changed.
- Skip a single checkout with `COPO_SKIP_SETUP=1 git checkout <branch>`.
- Override the target container with `COPO_WEB_CONTAINER=<name>`.
- If the stack isn't running, it prints the commands to run manually instead.


**Synopsis**

Packages installed using this approach only live in the container, 
not the local Docker image, so they are lost when the container is recreated 
(via `docker compose down`/`up`). The local Docker compose files circumvent this 
by running the same `pip install` every time `copo_web` service starts.

This enables the developer to only really need to rebuild the local Docker image 
for system-level changes (like apt packages or a new Python version).

Note: `pip install` does not remove packages that a branch has dropped. They 
stay installed until the container is recreated.
