from __future__ import annotations

import customtkinter as ctk

from .clipboard import copy_to_clipboard
from .generator import generate_spec
from .renderers import render_brief, render_card, render_sop

TAB_SOP = "自用 SOP"
TAB_BRIEF = "约文 Brief"
TAB_CARD = "灵感名片"


class KeikeuApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("keikeu")
        self.geometry("980x740")
        self.minsize(820, 600)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self,
            text="饼胚输入区",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 6))

        self.input_box = ctk.CTkTextbox(self, height=160, wrap="word")
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.input_box.insert(
            "0.0",
            "在这里粘贴你的口嗨 / 灵感 / CP 妄想…\n（示例：A 和 B 曾是一对 CP，某一天 B 变成了一只小虫…）",
        )

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.grid(row=2, column=0, sticky="new", padx=20, pady=(0, 8))
        button_row.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            button_row, text="生成饼胚", width=140, command=self._on_generate
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            button_row,
            text="清空",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self._on_clear,
        ).grid(row=0, column=1, padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            button_row, text="", text_color="#d33", anchor="w"
        )
        self.status_label.grid(row=0, column=2, sticky="ew")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.grid_rowconfigure(3, weight=3)

        self._output_boxes: dict[str, ctk.CTkTextbox] = {}
        for name in (TAB_SOP, TAB_BRIEF, TAB_CARD):
            tab = self.tabs.add(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            box = ctk.CTkTextbox(tab, wrap="word")
            box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            box.configure(state="disabled")
            self._output_boxes[name] = box

        ctk.CTkButton(
            self,
            text="复制当前 Markdown",
            width=200,
            command=self._on_copy,
        ).grid(row=4, column=0, sticky="e", padx=20, pady=(0, 18))

    def _set_output(self, tab_name: str, text: str) -> None:
        box = self._output_boxes[tab_name]
        box.configure(state="normal")
        box.delete("0.0", "end")
        box.insert("0.0", text)
        box.configure(state="disabled")

    def _on_generate(self) -> None:
        raw = self.input_box.get("0.0", "end")
        try:
            spec = generate_spec(raw)
        except ValueError as exc:
            self.status_label.configure(text=f"⚠ {exc}")
            return

        self.status_label.configure(text="")
        self._set_output(TAB_SOP, render_sop(spec))
        self._set_output(TAB_BRIEF, render_brief(spec))
        self._set_output(TAB_CARD, render_card(spec))

    def _on_clear(self) -> None:
        self.input_box.delete("0.0", "end")
        for name in self._output_boxes:
            self._set_output(name, "")
        self.status_label.configure(text="")

    def _on_copy(self) -> None:
        current = self.tabs.get()
        box = self._output_boxes.get(current)
        if box is None:
            return
        text = box.get("0.0", "end").rstrip("\n")
        if not text:
            self.status_label.configure(text="⚠ 当前 tab 还没有内容")
            return
        copy_to_clipboard(self, text)
        self.status_label.configure(
            text=f"✓ 已复制「{current}」的 Markdown", text_color="#2a7"
        )
        self.after(2500, lambda: self.status_label.configure(text="", text_color="#d33"))


def main() -> None:
    app = KeikeuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
