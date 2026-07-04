# DEBUG REPORT: NavigationRail Unbounded Height

- **Symptom:** Flet UI displayed `Error displaying NavigationRail: height is unbounded`.
- **Root cause:** The app set `page.scroll = ft.ScrollMode.AUTO` globally. In the main shell this put the top-level `Row` in a vertically unbounded scroll context, but `NavigationRail` requires bounded height.
- **Fix:** `_build_shell()` now disables page-level scrolling with `page.scroll = None`; `_build_vault_picker()` enables page-level scrolling only for the picker. Body pages keep their own internal scroll controls.
- **Evidence:** `rtk .venv/bin/python -m pytest -q` passed with 75 tests.
- **Regression test:** `tests/test_app_pages.py::test_navigation_shell_disables_page_level_scroll`.
- **Status:** DONE.
