# Road v0.3 fixture vaults

These frozen inputs contain synthetic author content only. They are not copied
from a real Vault.

- `mixed-vault/` covers schema v2/v3 coexistence, active root and one-level
  folders, Trash root and one-level folders, and one deliberately unsupported
  deep Paper path. Its v2 index is intentionally stale because Markdown remains
  authoritative.
- `unsafe-vault/` is valid fixture content for relocation tests. Tests place a
  copy outside a **simulated** Home; this repository fixture is never written to
  a genuinely unsafe location.
- Symlink cases are recipes in `manifest.json`. Tests create them only inside an
  ignored `tmp_path` copy because Git does not preserve the safety intent of a
  platform-created test symlink.

Phase 0 validates only this tree and its declared contracts. Runtime parsing of
schema v3 begins in Phase 2.
