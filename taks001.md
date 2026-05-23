# Task 001: Build keikeu v0.1 Demo

## Goal

Create a minimal runnable Python desktop GUI demo for `keikeu`.

`keikeu` converts one raw fanwork idea into three Markdown outputs:

1. SOP
2. Brief
3. Card

The demo validates the core product loop:

```text
raw fanwork rambling / 饼胚
→ structured creative spec
→ SOP / Brief / Card Markdown outputs
```

---

## Tech Constraints

- Language: Python
- GUI: CustomTkinter
- No AI API
- No database
- No account system
- No cloud sync
- No community features
- No image generation
- Use a local rule-based/mock generator
- Keep code beginner-readable

---

## User Flow

1. User opens the app.
2. User pastes a raw fanwork idea into the input box.
3. User clicks `生成饼胚`.
4. App generates:
   - 自用 SOP
   - 约文 Brief
   - 灵感名片
5. User switches between output tabs.
6. User can copy the current Markdown output.

---

## Required File Structure

Create this structure:

```text
keikeu/
  README.md
  SPEC.md
  TECH_SPEC.md
  requirements.txt
  src/
    keikeu/
      __init__.py
      app.py
      models.py
      generator.py
      renderers.py
      clipboard.py
  tests/
    test_generator.py
    test_renderers.py
  examples/
    bug_cp.txt
    output_sample.md
```

---

## Module Responsibilities

### `models.py`

Define the data structures.

Required model:

```python
from dataclasses import dataclass

@dataclass
class KeikeuSpec:
    raw_idea: str
    tags: list[str]
    vinegar: list[str]
    summary: str
    dumplings: list[str]
    final_form: str
    taboos: list[str]
    next_steps: list[str]
```

Keep it simple. Do not over-engineer nested models in v0.1.

---

### `generator.py`

Implement:

```python
def generate_spec(raw_idea: str) -> KeikeuSpec:
    ...
```

Rules:

- Preserve the original input as `raw_idea`.
- Generate mock/rule-based tags.
- Generate at least 3 vinegar items.
- Generate at least 3 dumpling items.
- Generate at least 3 next steps.
- If input is empty or whitespace, raise `ValueError`.

---

### `renderers.py`

Implement:

```python
def render_sop(spec: KeikeuSpec) -> str:
    ...

def render_brief(spec: KeikeuSpec) -> str:
    ...

def render_card(spec: KeikeuSpec) -> str:
    ...
```

Each renderer must return Markdown text.

---

### `clipboard.py`

Implement a clipboard copy helper.

If CustomTkinter/Tkinter clipboard handling is simpler directly from `app.py`, this file may contain only a minimal helper.

---

### `app.py`

Build the GUI.

Required UI:

- Window title: `keikeu`
- Large input text box labeled `饼胚输入区`
- Button: `生成饼胚`
- Button: `清空`
- Output tabs:
  - `自用 SOP`
  - `约文 Brief`
  - `灵感名片`
- Button: `复制当前 Markdown`
- Error message if input is empty
- App should run with:

```bash
python -m keikeu.app
```

---

## README.md Requirements

Include:

- What `keikeu` is
- How to install dependencies
- How to run the demo
- What v0.1 does not include
- English-Chinese bilinguo

---

## requirements.txt

Include:

```txt
customtkinter
pytest
```

---

## Tests

Write minimal pytest tests for:

- Empty input raises `ValueError`
- Non-empty input returns `KeikeuSpec`
- SOP renderer contains `# 饼胚 SOP`
- Brief renderer contains `# 约文 Brief`
- Card renderer contains `# 灵感名片`

---

## Acceptance Criteria

Done when:

- `python -m keikeu.app` launches the GUI
- User can generate SOP / Brief / Card from one input
- User can copy Markdown
- `pytest` passes
- Code stays simple and readable
- No AI API is used

---

## Agent Execution Instruction

Use this instruction when handing the task to Claude Code / Codex:

```text
Read the repo first. Then implement Task 001 exactly as specified.
Keep the demo minimal. Do not add AI APIs, databases, login, cloud sync, or extra frameworks.
After implementation, run pytest and report the result.
```

---

## Anti-Overengineering Rule

If the implementation starts adding any of the following, stop and simplify:

- Plugin architecture
- Database layer
- Auth system
- Cloud sync
- API client
- Agent framework
- Complex configuration system
- Abstract service layer
- Multi-window workflow

v0.1 is a demo. It should prove the product loop, not cosplay as a startup backend.
