# Road v0.4 JSONL Protocol v1

> **ARCHIVE — READ ONLY.** This is the completed Road v0.4 transport contract; active runtime facts live in source and tests.
>
> Current state: CP4 Python dispatcher plus Rust/Tauri host. Vue business slices
> begin at CP6.

The sidecar reads one UTF-8 JSON object per stdin line and writes exactly one
compact JSON response per stdout line. It does not use HTTP, ports, sockets, or
background networking.

## Handshake and envelope

Start the sidecar:

```bash
.venv/bin/python -m keikeu_bridge.sidecar
```

Then paste:

```json
{"v":1,"id":1,"method":"system.hello","params":{}}
```

The response has this shape:

```json
{"v":1,"id":1,"ok":true,"result":{"protocol_version":1,"session_id":"opaque-session","app_version":"0.1.0","core_version":"paper-v3/index-v3"}}
```

Every later request includes the returned top-level `session_id`:

```json
{"v":1,"id":2,"session_id":"opaque-session","method":"vault.inspect","params":{"path":"/Users/creator/keikeu-vault"}}
```

Success and error envelopes are:

```json
{"v":1,"id":2,"ok":true,"result":{}}
{"v":1,"id":2,"ok":false,"error":{"code":"validation_failed","message":"…","recovery":"correct_input","layer":"application_service"}}
```

- `v` is exactly `1`; `id` is a non-negative integer and is copied to the
  response.
- `params` is always an object. Unknown fields and wrong JSON types are
  `invalid_request`.
- `system.hello` has no `session_id`. A second hello creates a new session and
  expires every old preview, edit, and migration token.
- Transport errors use layer `jsonl_transport`; translated service/Core errors
  use `application_service`; an uncaught sidecar defect uses `python_sidecar`
  without placing exception details or author content on stdout.

## Methods

All methods may return `invalid_request`, `protocol_mismatch`, or
`session_expired` before the service call. “Never” means the host must not
automatically retry after the request was written; it must reload disk state
first if the response was lost.

| Method | Params → success result | Service method | Known service errors | Mutation / retry | Session token |
| --- | --- | --- | --- | --- | --- |
| `system.hello` | `{}` → protocol/session/app/Core versions | resets transient handles | `invalid_request`, `protocol_mismatch` | session reset / manual | none |
| `startup.load` | `{}` → `StartupDto` | `startup_load` | `unsafe_path`, `validation_failed`, `operation_failed` | local-state claim / never | `session_id` |
| `vault.inspect` | `{path}` → `VaultPreviewDto` | `vault_inspect` | `unsafe_path`, `validation_failed`, `preflight_blocked` | no durable write / manual | `session_id` |
| `vault.open` | `{preview_token}` → `StartupDto` | `vault_open` | `session_expired`, `stale_snapshot`, `validation_failed` | config/index / never | session + preview |
| `vault.initialize` | `{preview_token}` → `StartupDto` | `vault_initialize` | `session_expired`, `conflict`, `unsafe_path` | Vault/config / never | session + preview |
| `vault.relocate` | `{preview_token,destination_path}` → `StartupDto` | `vault_relocate` | `session_expired`, `unsafe_path`, `preflight_blocked`, `operation_failed` | copy/config / never | session + preview |
| `migration.preflight` | `{}` → `MigrationPreflightDto` | `migration_preflight` | `validation_failed`, `preflight_blocked` | no durable write / manual | `session_id` |
| `migration.run` | `{preflight_token}` → `MigrationResultDto` | `migration_run` | `session_expired`, `preflight_blocked`, `stale_snapshot`, `operation_failed` | backup/migrate/config / never | session + preflight |
| `paper.create_draft` | `{}` → `PaperDto` | `paper_create_draft` | `validation_failed` | memory only / manual | `session_id` |
| `paper.open` | `{path}` → `PaperDto` | `paper_open` | `not_found`, `unsafe_path`, `validation_failed` | memory only / manual | `session_id` |
| `paper.save` | `{edit_token,summary,display_name,highlights,tags}` → `PaperDto` | `paper_save` | `session_expired`, `stale_snapshot`, `conflict`, `validation_failed`, `operation_failed` | Paper/index / never | session + edit |
| `paper.soft_delete` | `{edit_token}` → `OperationReportDto` | `paper_soft_delete` | `session_expired`, `stale_snapshot`, `operation_failed` | Trash/index / never | session + edit |
| `flashcard.open` | `{path?}` → `FlashcardDeckDto` | `flashcard_open` | `not_found`, `unsafe_path`, `validation_failed` | disposable index / manual | `session_id` |
| `library.query` | `{scope?,search?,sort?}` → `LibraryViewDto` | `library_query` | `validation_failed`, `unsafe_path` | no requested rebuild / manual | `session_id` |
| `library.rebuild` | `{scope?,search?,sort?}` → `LibraryViewDto` | `library_query(rebuild=True)` | `validation_failed`, `operation_failed` | index / never | `session_id` |
| `library.move` | `{paths,destination_folder}` → report array | `library_move` | `not_found`, `conflict`, `stale_snapshot`, `operation_failed` | Paper/index / never | `session_id` |
| `library.branch` | `{path}` → `OperationReportDto` | `library_branch` | `not_found`, `conflict`, `stale_snapshot` | Paper/index / never | `session_id` |
| `library.soft_delete` | `{paths}` → report array | `library_soft_delete` | `not_found`, `stale_snapshot`, `operation_failed` | Trash/index / never | `session_id` |
| `library.restore` | `{paths}` → report array | `library_restore` | `not_found`, `conflict`, `operation_failed` | Paper/index / never | `session_id` |
| `library.permanently_delete` | `{paths}` → report array | `library_permanently_delete` | `not_found`, `operation_failed` | permanent delete/index / never | `session_id` |
| `library.create_folder` | `{name}` → folder name | `library_create_folder` | `validation_failed`, `conflict` | folder/index / never | `session_id` |
| `library.rename_folder` | `{folder,new_name}` → folder name | `library_rename_folder` | `not_found`, `validation_failed`, `conflict` | folder/index / never | `session_id` |
| `library.merge_folders` | `{source,destination}` → report array | `library_merge_folders` | `not_found`, `conflict`, `operation_failed` | Paper/folder/index / never | `session_id` |
| `library.soft_delete_folder` | `{folder}` → report array | `library_soft_delete_folder` | `not_found`, `operation_failed` | Trash/index / never | `session_id` |
| `library.restore_folder` | `{folder}` → report array | `library_restore_folder` | `not_found`, `conflict`, `operation_failed` | Paper/index / never | `session_id` |
| `library.permanently_delete_folder` | `{folder}` → `OperationReportDto` | `library_permanently_delete_folder` | `not_found`, `operation_failed` | permanent delete/index / never | `session_id` |
| `system.resolve_target` | `{action,relative_target}` → validated absolute `path` for Rust only | `resolve_system_target` | `not_found`, `unsafe_path`, `validation_failed` | no durable write / manual | `session_id` |

`system.resolve_target` is an internal Rust command dependency. Rust must use
the returned path immediately for the requested `open` or `reveal`; it must not
forward the absolute path to Vue or expose a general shell/open API.

## Rust host

- One Rust worker owns the child and serializes every request. Request IDs are
  monotonic within a host process.
- Startup and explicit restart perform `system.hello`; business requests remain
  blocked until it succeeds. Restart creates a new protocol session.
- Read, mutation, long-mutation, and hello timeouts are 20, 60, 600, and 10
  seconds respectively.
- Public bridge requests use the documented method allow-list.
  `system.resolve_target` stays internal to validated Rust open/reveal.
- The WebView capability grants no shell, dialog, or opener plugin permission.
  Vue can invoke only the registered narrow commands.

## Lost responses and shutdown

The Python dispatcher calls every method once and never retries. EOF ends the
sidecar with exit code `0`. Rust owns child crash detection, timeouts, request
serialization, response matching, restart, and exit cleanup.

If Rust wrote a mutation and then lost the response, it cannot know whether the
disk commit happened. It must return `commit_unknown`, must not automatically
resend the mutation, and must require a fresh query/open before another user
decision. `sidecar_unavailable` and `commit_unknown` are therefore reserved
host-layer errors, not fabricated by the CP3 Python dispatcher.

## Debug path

1. Check whether stdout is still one JSON response per input line.
2. Match `id`, then inspect `error.layer`.
3. For `jsonl_transport`, check envelope/version/session/params.
4. For `application_service`, reproduce through the matching service method on
   a synthetic/copied Vault.
5. Never paste Summary, Highlight content, real absolute paths, or unknown
   frontmatter into logs.
