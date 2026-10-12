"""Запуск приложения «Чудо Обувь»."""

from app.ui import CatalogWindow


def main():
    window = CatalogWindow()
    window.mainloop()


if __name__ == "__main__":
    main()
