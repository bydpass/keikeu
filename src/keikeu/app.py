from __future__ import annotations

import customtkinter as ctk

from .clipboard import copy_to_clipboard
from .generator import make_memo, make_ticket
from .models import Memo, Ticket
from .renderers import render_ticket

# --- pages (灵光池 → 配方票 → 写作调理) ---
PAGE_MEMO = "灵光池"
PAGE_TICKET = "配方票"
PAGE_REVIEW = "写作调理"
PAGES = (PAGE_MEMO, PAGE_TICKET, PAGE_REVIEW)

# --- Ticket output modes: sidebar label -> renderer mode ---
MODE_LABELS = {"自用 SOP": "SOP", "约文 Brief": "Brief", "灵感名片": "Card"}

# --- review targets (skeleton, IO_NEO §3) ---
REVIEW_TARGETS = ("结构", "情绪", "人物", "节奏", "OOC", "雷点", "读者体感", "约稿清晰度")

# --- palette: green accent on cream ---
CREAM = "#e8e5df"
CREAM_DARK = "#dcd8cf"
CREAM_LIGHT = "#f2f0ea"
GREEN = "#4a7c59"
GREEN_HOVER = "#3d6849"
INK = "#2c2a26"
OK = "#2a7"
ERR = "#d33"


class KeikeuApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("keikeu")
        self.geometry("980x740")
        self.minsize(820, 600)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=CREAM)

        self._title_font = ctk.CTkFont(family="Noto Serif SC", size=22, weight="bold")
        self._brand_font = ctk.CTkFont(family="Noto Serif SC", size=24, weight="bold")
        self._mono_font = ctk.CTkFont(family="IBM Plex Mono", size=13)

        # state
        self.current_memo: Memo | None = None
        self.current_ticket: Ticket | None = None
        self.active_page: str = PAGE_MEMO

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

        self._page_frames: dict[str, ctk.CTkFrame] = {}
        self._build_memo_page()
        self._build_ticket_page()
        self._build_review_page()

        self._show_page(PAGE_MEMO)

    # ---------- shell ----------
    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=CREAM_DARK)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)

        ctk.CTkLabel(
            bar, text="keikeu", font=self._brand_font, text_color=GREEN, anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 4))
        ctk.CTkLabel(
            bar, text="同人药剂师 · 幽灵助手", font=ctk.CTkFont(size=11),
            text_color=INK, anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 22))

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        for i, name in enumerate(PAGES):
            btn = ctk.CTkButton(
                bar, text=name, anchor="w", height=44, corner_radius=8,
                command=lambda n=name: self._show_page(n),
            )
            btn.grid(row=2 + i, column=0, sticky="ew", padx=14, pady=4)
            self._nav_buttons[name] = btn

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self, fg_color=CREAM)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._page_area = ctk.CTkFrame(content, fg_color="transparent")
        self._page_area.grid(row=0, column=0, sticky="nsew")
        self._page_area.grid_columnconfigure(0, weight=1)
        self._page_area.grid_rowconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            content, text="", text_color=ERR, anchor="w", height=24
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

    def _new_page(self, name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._page_area, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        self._page_frames[name] = frame
        return frame

    def _show_page(self, name: str) -> None:
        self.active_page = name
        self._page_frames[name].tkraise()
        for n, btn in self._nav_buttons.items():
            if n == name:
                btn.configure(fg_color=GREEN, hover_color=GREEN_HOVER, text_color="#fff")
            else:
                btn.configure(
                    fg_color="transparent", hover_color=CREAM_LIGHT, text_color=INK
                )

    def _status(self, text: str, color: str = ERR) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _flash_ok(self, text: str) -> None:
        self._status(text, OK)
        self.after(2500, lambda: self._status(""))

    # ---------- Memo page ----------
    def _build_memo_page(self) -> None:
        page = self._new_page(PAGE_MEMO)
        page.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            page, text="灵光池 Memo", font=self._title_font, text_color=INK, anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 2))
        ctk.CTkLabel(
            page,
            text=(
                "可以直接乱写。  小技巧：**核心脑洞**　*情绪味道*　[待定]　! 禁忌/雷点\n"
                "（示例：A 和 B 曾是一对 CP，某一天 B 变成了一只小虫…）"
            ),
            font=ctk.CTkFont(size=12), text_color="#6b675f", anchor="w", justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

        self.memo_input = ctk.CTkTextbox(
            page, wrap="word", fg_color=CREAM_LIGHT, border_width=1, border_color=CREAM_DARK
        )
        self.memo_input.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 12))

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 16))
        ctk.CTkButton(
            row, text="保存灵感 → 配方票", width=170, fg_color=GREEN,
            hover_color=GREEN_HOVER, command=self._on_save_memo,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            row, text="清空", width=80, fg_color="transparent", border_width=1,
            border_color=CREAM_DARK, text_color=INK, hover_color=CREAM_LIGHT,
            command=self._on_clear_memo,
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            row, text="保存 Markdown", width=130, state="disabled",
            command=self._on_save_markdown,
        ).grid(row=0, column=2)

    def _on_save_memo(self) -> None:
        raw = self.memo_input.get("0.0", "end")
        if not raw.strip():
            self._status("先写点东西。")
            return
        self.current_memo = make_memo(raw)
        self._show_page(PAGE_TICKET)
        self._flash_ok("✓ 灵感已收进灵光池")

    def _on_clear_memo(self) -> None:
        self.memo_input.delete("0.0", "end")
        self._status("")

    # ---------- Ticket page ----------
    def _build_ticket_page(self) -> None:
        page = self._new_page(PAGE_TICKET)
        page.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            page, text="配方票 Ticket", font=self._title_font, text_color=INK, anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 8))

        self.mode_switch = ctk.CTkSegmentedButton(
            page, values=list(MODE_LABELS.keys()), command=self._on_switch_mode,
            selected_color=GREEN, selected_hover_color=GREEN_HOVER,
        )
        self.mode_switch.set("自用 SOP")
        self.mode_switch.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))

        # receipt-styled output
        self.ticket_output = ctk.CTkTextbox(
            page, wrap="word", font=self._mono_font, fg_color=CREAM_LIGHT,
            border_width=1, border_color=CREAM_DARK,
        )
        self.ticket_output.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self.ticket_output.configure(state="disabled")

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 16))
        ctk.CTkButton(
            row, text="生成配方票", width=130, fg_color=GREEN,
            hover_color=GREEN_HOVER, command=self._on_generate_ticket,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            row, text="复制 Markdown", width=140, command=self._on_copy_ticket
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            row, text="保存 Markdown", width=130, state="disabled",
            command=self._on_save_markdown,
        ).grid(row=0, column=2)

    def _set_ticket_output(self, text: str) -> None:
        self.ticket_output.configure(state="normal")
        self.ticket_output.delete("0.0", "end")
        self.ticket_output.insert("0.0", text)
        self.ticket_output.configure(state="disabled")

    def _render_current_mode(self) -> None:
        if self.current_ticket is None:
            return
        mode = MODE_LABELS[self.mode_switch.get()]
        self._set_ticket_output(render_ticket(self.current_ticket, mode))

    def _on_switch_mode(self, _value: str) -> None:
        self._render_current_mode()

    def _on_generate_ticket(self) -> None:
        if self.current_memo is None:
            self._status("先在灵光池写点东西。")
            return
        try:
            self.current_ticket = make_ticket(self.current_memo.raw)
        except ValueError as exc:
            self._status(f"⚠ {exc}")
            return
        self._status("")
        self._render_current_mode()

    def _on_copy_ticket(self) -> None:
        if self.current_ticket is None:
            self._status("先生成配方票。")
            return
        text = self.ticket_output.get("0.0", "end").rstrip("\n")
        if not text:
            self._status("先生成配方票。")
            return
        copy_to_clipboard(self, text)
        self._flash_ok(f"✓ 已复制「{self.mode_switch.get()}」的 Markdown")

    # ---------- Review page (skeleton, v0.2) ----------
    def _build_review_page(self) -> None:
        page = self._new_page(PAGE_REVIEW)
        page.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            page, text="写作调理 Review", font=self._title_font, text_color=INK, anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 2))
        ctk.CTkLabel(
            page, text="试药包 v0.2，骨架占位，尚未实现。", font=ctk.CTkFont(size=12),
            text_color="#6b675f", anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

        self.draft_input = ctk.CTkTextbox(
            page, height=140, wrap="word", fg_color=CREAM_LIGHT,
            border_width=1, border_color=CREAM_DARK,
        )
        self.draft_input.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 10))

        targets = ctk.CTkFrame(page, fg_color="transparent")
        targets.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 10))
        for i, t in enumerate(REVIEW_TARGETS):
            ctk.CTkCheckBox(targets, text=t, fg_color=GREEN, hover_color=GREEN_HOVER).grid(
                row=i // 4, column=i % 4, sticky="w", padx=6, pady=4
            )

        self.review_output = ctk.CTkTextbox(
            page, wrap="word", font=self._mono_font, fg_color=CREAM_LIGHT,
            border_width=1, border_color=CREAM_DARK,
        )
        self.review_output.grid(row=4, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self.review_output.configure(state="disabled")

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 16))
        ctk.CTkButton(
            row, text="生成试药包", width=130, fg_color=GREEN,
            hover_color=GREEN_HOVER, command=self._on_generate_review,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            row, text="复制 skill.md", width=130, state="disabled"
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            row, text="保存 Markdown", width=130, state="disabled",
            command=self._on_save_markdown,
        ).grid(row=0, column=2)

    def _on_generate_review(self) -> None:
        self._status("试药包还没造好（v0.2）。")

    # ---------- export (skeleton, Phase 4) ----------
    def _on_save_markdown(self) -> None:
        self._status("保存功能待实现")


def main() -> None:
    app = KeikeuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
