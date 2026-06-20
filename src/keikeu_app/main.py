import flet as ft


def main(page: ft.Page) -> None:
    page.title = "keikeu"
    page.add(ft.Text("keikeu — scaffold placeholder"))


if __name__ == "__main__":
    ft.app(target=main)
