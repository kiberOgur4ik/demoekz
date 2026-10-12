"""Главное окно и строки каталога на Tkinter/ttk."""

import queue
import threading
import tkinter as tk
from datetime import date
from tkinter import font, ttk

import psycopg2
from app.database import load_catalog
from app.images import PROJECT_DIR, ImageCache
from app.models import CatalogProduct
from app.pricing import format_price

BACKGROUND = "#F3F6F4"
HEADER = "#E8F5EE"
ROW_BACKGROUND = "#FFFFFF"
LOW_STOCK_BACKGROUND = "#FDE7E7"
TEXT = "#202B25"
SECONDARY = "#4D6054"
ACCENT = "#256344"
WARNING = "#8D2727"
BORDER = "#CBD8CF"


class ProductRow(tk.Frame):
    def __init__(self, parent, product: CatalogProduct, images: ImageCache, fonts):
        background = LOW_STOCK_BACKGROUND if product.low_stock else ROW_BACKGROUND
        super().__init__(
            parent,
            background=background,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=16,
            pady=16,
        )
        self.product = product
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, minsize=180)

        photo_frame = tk.Frame(self, width=140, height=110, background=background)
        photo_frame.grid(row=0, column=0, sticky="n", padx=(0, 16))
        photo_frame.grid_propagate(False)
        self.photo = images.get(product.image_path, (140, 110))
        photo_label = tk.Label(photo_frame, background=background)
        photo_label.grid(row=0, column=0, sticky="nsew")
        photo_frame.rowconfigure(0, weight=1)
        photo_frame.columnconfigure(0, weight=1)
        if self.photo is None:
            photo_label.configure(
                text="Нет фото", font=fonts["body"], foreground=SECONDARY
            )
        else:
            photo_label.configure(image=self.photo)

        info = tk.Frame(self, background=background)
        info.grid(row=0, column=1, sticky="nsew", padx=(0, 16))
        info.columnconfigure(0, weight=1)
        title = f"{product.manufacturer} | {product.name}"
        quantity = f"Количество пар: {product.available_qty}"
        if product.low_stock:
            quantity += " · Мало в наличии"
        self.info_labels = []
        for index, (text, text_font, color) in enumerate(
            [
                (title, fonts["title"], TEXT),
                (f"Категория: {product.category}", fonts["body"], TEXT),
                (quantity, fonts["body"], WARNING if product.low_stock else TEXT),
                (f"Состав: {product.composition}", fonts["body"], SECONDARY),
            ]
        ):
            label = tk.Label(
                info,
                text=text,
                font=text_font,
                foreground=color,
                background=background,
                anchor="w",
                justify="left",
                wraplength=440,
            )
            label.grid(
                row=index, column=0, sticky="ew", pady=(0, 8 if index == 0 else 4)
            )
            self.info_labels.append(label)
        info.bind("<Configure>", self._wrap_text)

        prices = tk.Frame(self, background=background)
        prices.grid(row=0, column=2, sticky="ne")
        tk.Label(
            prices,
            text="Цена со скидкой" if product.has_discount else "Цена",
            font=fonts["body"],
            foreground=SECONDARY,
            background=background,
        ).pack(anchor="e")
        tk.Label(
            prices,
            text=format_price(product.final_price),
            font=fonts["price"],
            foreground=TEXT,
            background=background,
        ).pack(anchor="e", pady=(4, 0))
        if product.has_discount:
            tk.Label(
                prices,
                text=format_price(product.base_price),
                font=fonts["old_price"],
                foreground=SECONDARY,
                background=background,
            ).pack(anchor="e", pady=(4, 0))
            tk.Label(
                prices,
                text="Скидка 25%",
                font=fonts["body"],
                foreground=ACCENT,
                background=background,
            ).pack(anchor="e", pady=(4, 0))

    def _wrap_text(self, event):
        for label in self.info_labels:
            label.configure(wraplength=max(40, event.width - 4))


class CatalogWindow(tk.Tk):
    def __init__(self, catalog_loader=load_catalog, today=date.today):
        super().__init__()
        self.title("Чудо Обувь — Каталог обуви")
        self.minsize(900, 600)
        self.geometry("1100x760")
        self.configure(background=BACKGROUND)
        self.catalog_loader = catalog_loader
        self.today = today
        self.results = queue.Queue()
        self.loading = False
        self.closed = False
        self.poll_job = None
        self.rows = []
        self.products = []
        self.images = ImageCache(self)
        self.fonts = self._create_fonts()
        self._create_styles()
        self._set_icon()
        self._build_window()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<MouseWheel>", self._scroll_mouse)
        self.bind("<Button-4>", lambda event: self._scroll_units(-3))
        self.bind("<Button-5>", lambda event: self._scroll_units(3))
        self.bind("<Prior>", lambda event: self._scroll_page(-1))
        self.bind("<Next>", lambda event: self._scroll_page(1))
        self.bind("<Control-Home>", lambda event: self.canvas.yview_moveto(0))
        self.bind("<Control-End>", lambda event: self.canvas.yview_moveto(1))
        self.bind("<F5>", lambda event: self.refresh())
        self.bind("<Control-r>", lambda event: self.refresh())
        if self.tk.call("tk", "windowingsystem") == "aqua":
            self.bind("<Command-r>", lambda event: self.refresh())
        self.after(0, self.refresh)

    def _create_fonts(self):
        family = font.nametofont("TkDefaultFont").actual("family")
        return {
            "body": font.Font(self, family=family, size=11),
            "title": font.Font(self, family=family, size=12, weight="bold"),
            "heading": font.Font(self, family=family, size=19, weight="bold"),
            "price": font.Font(self, family=family, size=17, weight="bold"),
            "old_price": font.Font(self, family=family, size=10, overstrike=True),
        }

    def _create_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Refresh.TButton",
            font=self.fonts["body"],
            padding=(16, 10),
            background=ACCENT,
            foreground="white",
            borderwidth=1,
        )
        style.map(
            "Refresh.TButton",
            background=[("disabled", "#D8E4DC"), ("active", "#194D32")],
            foreground=[("disabled", SECONDARY)],
        )
        style.configure(
            "Vertical.TScrollbar", background="#D5E0D9", troughcolor=BACKGROUND
        )

    def _set_icon(self):
        self.icon_image = self.images.get("assets/logo.png", (64, 64))
        if self.icon_image is not None:
            self.iconphoto(True, self.icon_image)
        if self.tk.call("tk", "windowingsystem") == "win32":
            try:
                self.iconbitmap(str(PROJECT_DIR / "assets/app.ico"))
            except tk.TclError:
                if self.icon_image is not None:
                    self.iconphoto(True, self.icon_image)

    def _build_window(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = tk.Frame(self, background=HEADER, padx=24, pady=16)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        self.logo = self.images.get("assets/logo.png", (64, 64))
        tk.Label(header, image=self.logo, background=HEADER).grid(
            row=0,
            column=0,
            padx=(0, 16),
            sticky="w",
        )
        heading = tk.Frame(header, background=HEADER)
        heading.grid(row=0, column=1, sticky="w")
        tk.Label(
            heading,
            text="Чудо Обувь",
            background=HEADER,
            foreground=TEXT,
            font=self.fonts["heading"],
        ).pack(anchor="w")
        tk.Label(
            heading,
            text="Каталог обуви",
            background=HEADER,
            foreground=SECONDARY,
            font=self.fonts["body"],
        ).pack(anchor="w", pady=(4, 0))
        self.refresh_button = ttk.Button(
            header, text="Обновить", style="Refresh.TButton", command=self.refresh
        )
        self.refresh_button.grid(row=0, column=2, sticky="e")

        self.content = tk.Frame(self, background=BACKGROUND)
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self.content,
            background=BACKGROUND,
            highlightthickness=1,
            highlightbackground=BACKGROUND,
            highlightcolor=ACCENT,
            takefocus=True,
            yscrollincrement=20,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(
            self.content, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.list_frame = tk.Frame(self.canvas, background=BACKGROUND)
        self.list_id = self.canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw"
        )
        self.list_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_list)

        self.state_frame = tk.Frame(self.content, background=BACKGROUND)
        self.state_label = tk.Label(
            self.state_frame,
            background=BACKGROUND,
            foreground=SECONDARY,
            font=self.fonts["body"],
            justify="center",
            wraplength=620,
        )
        self.state_label.pack(pady=(0, 16))
        self.retry_button = ttk.Button(
            self.state_frame,
            text="Повторить",
            style="Refresh.TButton",
            command=self.refresh,
        )

        footer = tk.Frame(self, background=BACKGROUND, padx=24, pady=12)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.status = tk.Label(
            footer,
            background=BACKGROUND,
            foreground=SECONDARY,
            font=self.fonts["body"],
            anchor="w",
        )
        self.status.grid(row=0, column=0, sticky="w")
        self.price_date = tk.Label(
            footer, background=BACKGROUND, foreground=SECONDARY, font=self.fonts["body"]
        )
        self.price_date.grid(row=0, column=1, sticky="e")

    def _update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_list(self, event):
        self.canvas.itemconfigure(self.list_id, width=event.width - 2)

    def _scroll_units(self, units):
        if self.canvas.winfo_ismapped():
            self.canvas.yview_scroll(units, "units")
        return "break"

    def _scroll_mouse(self, event):
        if self.tk.call("tk", "windowingsystem") == "aqua":
            units = -int(event.delta)
        else:
            units = -int(event.delta / 120) * 3
        return self._scroll_units(units)

    def _scroll_page(self, direction):
        if self.canvas.winfo_ismapped():
            self.canvas.yview_scroll(direction, "pages")
        return "break"

    def _show_state(self, text, retry=False):
        self.canvas.grid_remove()
        self.scrollbar.grid_remove()
        self.state_frame.grid(row=0, column=0, sticky="")
        self.state_label.configure(text=text)
        if retry:
            self.retry_button.pack()
        else:
            self.retry_button.pack_forget()

    def refresh(self):
        if self.loading or self.closed:
            return
        self.loading = True
        self.refresh_button.state(["disabled"])
        self.retry_button.state(["disabled"])
        self.calculation_date = self.today()
        self.status.configure(text="Загрузка каталога…")
        if not self.products or not self.canvas.winfo_ismapped():
            self._show_state("Загрузка каталога…")
        worker = threading.Thread(
            target=self._load_in_background, args=(self.calculation_date,), daemon=True
        )
        worker.start()
        self.poll_job = self.after(80, self._poll_result)

    def _load_in_background(self, calculation_date):
        try:
            products = self.catalog_loader(calculation_date)
        except (psycopg2.Error, OSError, ValueError, TypeError):
            self.results.put(("error", None))
        else:
            self.results.put(("success", products))

    def _poll_result(self):
        self.poll_job = None
        if self.closed:
            return
        try:
            state, products = self.results.get_nowait()
        except queue.Empty:
            self.poll_job = self.after(80, self._poll_result)
            return
        self.loading = False
        self.refresh_button.state(["!disabled"])
        self.retry_button.state(["!disabled"])
        if state == "error":
            self._show_state(
                "Не удалось загрузить каталог.\n"
                "Проверьте подключение к базе и повторите попытку.",
                retry=True,
            )
            self.status.configure(text="Каталог не загружен")
            self.price_date.configure(text="")
        else:
            self._show_products(products)

    def _show_products(self, products):
        old_position = self.canvas.yview()[0] if self.products else 0
        for row in self.rows:
            row.destroy()
        self.rows.clear()
        self.images.clear()
        self.products = products
        total = sum(product.available_qty for product in products)
        self.status.configure(
            text=f"Моделей: {len(products)} · Пар: {total:,}".replace(",", " ")
        )
        self.price_date.configure(text=f"Цены на {self.calculation_date:%d.%m.%Y}")
        if not products:
            self._show_state("В каталоге пока нет моделей обуви.")
            return
        self.state_frame.grid_remove()
        self.canvas.grid()
        self.scrollbar.grid()
        for product in products:
            row = ProductRow(self.list_frame, product, self.images, self.fonts)
            row.pack(fill="x", pady=(0, 12))
            self.rows.append(row)
        self.update_idletasks()
        self._update_scroll_region()
        self.canvas.yview_moveto(old_position)

    def report_callback_exception(self, _error_type, _error, _traceback):
        self.loading = False
        self.refresh_button.state(["!disabled"])
        self.retry_button.state(["!disabled"])
        self._show_state(
            "Не удалось отобразить каталог.\n"
            "Повторите загрузку.",
            retry=True,
        )

    def close(self):
        self.closed = True
        if self.poll_job is not None:
            self.after_cancel(self.poll_job)
        self.destroy()
