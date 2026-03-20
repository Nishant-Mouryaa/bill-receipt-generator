import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import sys
from datetime import datetime

from database import (
    init_db, save_bill, fetch_all_bills, fetch_bill_items,
    delete_bill, search_bills, get_total_revenue, get_total_bills_count,
    get_average_bill_amount, get_top_customers, get_top_items,
    get_monthly_revenue, get_revenue_by_date
)
from receipt_generator import generate_receipt
from currency import (
    get_currency_list, get_symbol, format_currency,
    CURRENCIES, DEFAULT_CURRENCY
)

# Charts - optional import with fallback
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False

# ── Colour Palette ───────────────────────────────────────────
BG        = "#F0F4F8"
PRIMARY   = "#2C3E50"
ACCENT    = "#3498DB"
SUCCESS   = "#27AE60"
DANGER    = "#E74C3C"
WHITE     = "#FFFFFF"
LIGHT     = "#ECF0F1"
TEXT      = "#2C3E50"
WARNING   = "#F39C12"

FONT_TITLE  = ("Helvetica", 20, "bold")
FONT_LABEL  = ("Helvetica", 11)
FONT_BOLD   = ("Helvetica", 11, "bold")
FONT_SMALL  = ("Helvetica", 9)
FONT_BUTTON = ("Helvetica", 11, "bold")
FONT_LARGE  = ("Helvetica", 24, "bold")


class BillApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧾 Bill Receipt Generator")
        self.geometry("1100x750")
        self.resizable(True, True)
        self.configure(bg=BG)

        init_db()
        self.items = []
        self.current_currency = DEFAULT_CURRENCY
        self._build_ui()

    def _build_ui(self):
        self._build_header()
        self._build_notebook()
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=PRIMARY, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="🧾  Bill Receipt Generator",
            font=FONT_TITLE, bg=PRIMARY, fg=WHITE
        ).pack(side="left", padx=20, pady=15)

        tk.Label(
            hdr, text=datetime.now().strftime("%A, %d %B %Y"),
            font=FONT_SMALL, bg=PRIMARY, fg=LIGHT
        ).pack(side="right", padx=20)

    def _build_notebook(self):
        """Build tabbed interface for different views."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", font=FONT_BOLD, padding=[15, 8])
        style.map("TNotebook.Tab", background=[("selected", ACCENT)])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Create tabs
        self.bill_tab = tk.Frame(self.notebook, bg=BG)
        self.history_tab = tk.Frame(self.notebook, bg=BG)
        self.dashboard_tab = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.bill_tab, text="  📝 New Bill  ")
        self.notebook.add(self.history_tab, text="  📋 Bill History  ")
        self.notebook.add(self.dashboard_tab, text="  📊 Dashboard  ")

        # Build each tab
        self._build_bill_tab()
        self._build_history_tab()
        self._build_dashboard_tab()

        # Refresh data when switching tabs
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        """Handle tab change events."""
        selected = self.notebook.index(self.notebook.select())
        if selected == 1:  # History tab
            self._refresh_history()
        elif selected == 2:  # Dashboard tab
            self._refresh_dashboard()

    # ══════════════════════════════════════════════════════════════
    # NEW BILL TAB
    # ══════════════════════════════════════════════════════════════
    def _build_bill_tab(self):
        self._build_form()
        self._build_items_section()
        self._build_buttons()

    def _build_form(self):
        frame = tk.LabelFrame(
            self.bill_tab, text=" 📋 Bill Information ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY,
            padx=10, pady=10
        )
        frame.pack(fill="x", padx=20, pady=(15, 5))

        # Row 1
        row1 = tk.Frame(frame, bg=BG)
        row1.pack(fill="x", pady=4)

        self._label(row1, "Bill No:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.bill_no_var = tk.StringVar(value=self._generate_bill_no())
        self._entry(row1, self.bill_no_var, width=18).grid(row=0, column=1, padx=(0, 15))

        self._label(row1, "Customer Name:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.customer_var = tk.StringVar()
        self._entry(row1, self.customer_var, width=25).grid(row=0, column=3, padx=(0, 15))

        self._label(row1, "Tax (%):").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.tax_var = tk.StringVar(value="0")
        self._entry(row1, self.tax_var, width=6).grid(row=0, column=5, padx=(0, 15))

        # Currency dropdown
        self._label(row1, "Currency:").grid(row=0, column=6, sticky="w", padx=(0, 5))
        self.currency_var = tk.StringVar(value=DEFAULT_CURRENCY)
        currency_combo = ttk.Combobox(
            row1, textvariable=self.currency_var,
            values=get_currency_list(), state="readonly", width=8
        )
        currency_combo.grid(row=0, column=7)
        currency_combo.bind("<<ComboboxSelected>>", self._on_currency_change)

    def _on_currency_change(self, event=None):
        """Update UI when currency changes."""
        self.current_currency = self.currency_var.get()
        self._update_total()
        self._refresh_tree_currency()

    def _refresh_tree_currency(self):
        """Refresh tree display with new currency symbol."""
        symbol = get_symbol(self.current_currency)
        for i, row_id in enumerate(self.tree.get_children()):
            item = self.items[i]
            self.tree.item(row_id, values=(
                i + 1,
                item["name"],
                item["qty"],
                f"{symbol}{item['price']:.2f}",
                f"{symbol}{item['subtotal']:.2f}"
            ))

    def _build_items_section(self):
        # ── Input row for adding items ──
        add_frame = tk.LabelFrame(
            self.bill_tab, text=" ➕ Add Item ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY,
            padx=10, pady=10
        )
        add_frame.pack(fill="x", padx=20, pady=5)

        row = tk.Frame(add_frame, bg=BG)
        row.pack(fill="x")

        self._label(row, "Item Name:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.item_name_var = tk.StringVar()
        self._entry(row, self.item_name_var, width=28).grid(row=0, column=1, padx=(0, 15))

        self._label(row, "Quantity:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.qty_var = tk.StringVar(value="1")
        self._entry(row, self.qty_var, width=8).grid(row=0, column=3, padx=(0, 15))

        symbol = get_symbol(self.current_currency)
        self._label(row, f"Unit Price:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.price_var = tk.StringVar(value="0.00")
        self._entry(row, self.price_var, width=10).grid(row=0, column=5, padx=(0, 15))

        tk.Button(
            row, text="➕ Add Item",
            font=FONT_BUTTON, bg=ACCENT, fg=WHITE,
            relief="flat", cursor="hand2",
            padx=10, pady=4,
            command=self._add_item
        ).grid(row=0, column=6, padx=(10, 0))

        # ── Items Treeview ──
        tree_frame = tk.Frame(self.bill_tab, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)

        cols = ("#", "Item Name", "Quantity", "Unit Price", "Subtotal")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)

        col_widths = [40, 320, 90, 120, 120]
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.column("Item Name", anchor="w")

        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._style_treeview()

        # Total label
        self.total_var = tk.StringVar(value="Total: $0.00")
        tk.Label(
            self.bill_tab, textvariable=self.total_var,
            font=("Helvetica", 13, "bold"),
            bg=BG, fg=DANGER
        ).pack(anchor="e", padx=25)

    def _style_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=WHITE, foreground=TEXT,
                        rowheight=28, fieldbackground=WHITE, font=FONT_LABEL)
        style.configure("Treeview.Heading",
                        background=PRIMARY, foreground=WHITE,
                        font=FONT_BOLD, relief="flat")
        style.map("Treeview", background=[("selected", ACCENT)])

    def _build_buttons(self):
        btn_frame = tk.Frame(self.bill_tab, bg=BG)
        btn_frame.pack(fill="x", padx=20, pady=10)

        buttons = [
            ("🗑️  Remove Selected", DANGER, self._remove_item),
            ("🔄  Clear All", "#7F8C8D", self._clear_all),
            ("💾  Save & Generate", SUCCESS, self._save_and_generate),
        ]
        for text, color, cmd in buttons:
            tk.Button(
                btn_frame, text=text,
                font=FONT_BUTTON, bg=color, fg=WHITE,
                relief="flat", cursor="hand2",
                padx=15, pady=8,
                command=cmd
            ).pack(side="right", padx=5)

    # ══════════════════════════════════════════════════════════════
    # BILL HISTORY TAB
    # ══════════════════════════════════════════════════════════════
    def _build_history_tab(self):
        # Search frame
        search_frame = tk.Frame(self.history_tab, bg=BG)
        search_frame.pack(fill="x", padx=20, pady=10)

        self._label(search_frame, "Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = self._entry(search_frame, self.search_var, width=30)
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.bind("<Return>", lambda e: self._search_bills())

        tk.Button(
            search_frame, text="🔍 Search",
            font=FONT_BUTTON, bg=ACCENT, fg=WHITE,
            relief="flat", cursor="hand2",
            command=self._search_bills
        ).pack(side="left", padx=5)

        tk.Button(
            search_frame, text="🔄 Refresh",
            font=FONT_BUTTON, bg=PRIMARY, fg=WHITE,
            relief="flat", cursor="hand2",
            command=self._refresh_history
        ).pack(side="left", padx=5)

        # History treeview
        tree_frame = tk.Frame(self.history_tab, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)

        cols = ("ID", "Bill No", "Customer", "Date", "Total", "Currency")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)

        col_widths = [50, 180, 200, 180, 120, 80]
        for col, w in zip(cols, col_widths):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=w, anchor="center")
        self.history_tree.column("Customer", anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Double-click to view details
        self.history_tree.bind("<Double-1>", self._view_bill_details)

        # Action buttons
        btn_frame = tk.Frame(self.history_tab, bg=BG)
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(
            btn_frame, text="👁️ View Details",
            font=FONT_BUTTON, bg=ACCENT, fg=WHITE,
            relief="flat", cursor="hand2",
            command=lambda: self._view_bill_details(None)
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="🗑️ Delete Bill",
            font=FONT_BUTTON, bg=DANGER, fg=WHITE,
            relief="flat", cursor="hand2",
            command=self._delete_selected_bill
        ).pack(side="left", padx=5)

        # Stats label
        self.history_stats_var = tk.StringVar(value="")
        tk.Label(
            btn_frame, textvariable=self.history_stats_var,
            font=FONT_SMALL, bg=BG, fg=TEXT
        ).pack(side="right", padx=10)

    def _refresh_history(self):
        """Refresh the bill history list."""
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        bills = fetch_all_bills()
        for bill in bills:
            bill_id, bill_no, customer, date, total, created_at, currency = bill
            symbol = get_symbol(currency)
            self.history_tree.insert("", "end", values=(
                bill_id, bill_no, customer, date,
                f"{symbol}{total:.2f}", currency
            ))

        self.history_stats_var.set(f"Total Bills: {len(bills)}")

    def _search_bills(self):
        """Search bills by customer or bill number."""
        search_term = self.search_var.get().strip()
        if not search_term:
            self._refresh_history()
            return

        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        bills = search_bills(search_term)
        for bill in bills:
            bill_id, bill_no, customer, date, total, created_at, currency = bill
            symbol = get_symbol(currency)
            self.history_tree.insert("", "end", values=(
                bill_id, bill_no, customer, date,
                f"{symbol}{total:.2f}", currency
            ))

        self.history_stats_var.set(f"Found: {len(bills)} bills")

    def _view_bill_details(self, event):
        """Show bill details in a popup window."""
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a bill to view.")
            return

        values = self.history_tree.item(selected[0])["values"]
        bill_no = values[1]
        customer = values[2]
        date = values[3]
        total = values[4]
        currency = values[5]

        items = fetch_bill_items(bill_no)

        # Create detail window
        detail_win = tk.Toplevel(self)
        detail_win.title(f"Bill Details - {bill_no}")
        detail_win.geometry("500x400")
        detail_win.configure(bg=BG)

        # Header
        tk.Label(
            detail_win, text=f"📋 Bill: {bill_no}",
            font=FONT_TITLE, bg=BG, fg=PRIMARY
        ).pack(pady=10)

        # Info frame
        info_frame = tk.Frame(detail_win, bg=BG)
        info_frame.pack(fill="x", padx=20, pady=5)

        labels = [
            ("Customer:", customer),
            ("Date:", date),
            ("Currency:", currency),
            ("Total:", total),
        ]
        for label, value in labels:
            row = tk.Frame(info_frame, bg=BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=FONT_BOLD, bg=BG, fg=TEXT, width=10, anchor="e").pack(side="left")
            tk.Label(row, text=value, font=FONT_LABEL, bg=BG, fg=TEXT).pack(side="left", padx=5)

        # Items list
        tk.Label(
            detail_win, text="Items:",
            font=FONT_BOLD, bg=BG, fg=TEXT
        ).pack(anchor="w", padx=20, pady=(10, 5))

        items_frame = tk.Frame(detail_win, bg=WHITE, relief="solid", bd=1)
        items_frame.pack(fill="both", expand=True, padx=20, pady=5)

        symbol = get_symbol(currency)
        for i, item in enumerate(items, 1):
            item_name, qty, price, subtotal = item
            item_text = f"{i}. {item_name} × {qty} @ {symbol}{price:.2f} = {symbol}{subtotal:.2f}"
            tk.Label(
                items_frame, text=item_text,
                font=FONT_LABEL, bg=WHITE, fg=TEXT, anchor="w"
            ).pack(fill="x", padx=10, pady=2)

        # Close button
        tk.Button(
            detail_win, text="Close",
            font=FONT_BUTTON, bg=PRIMARY, fg=WHITE,
            relief="flat", command=detail_win.destroy
        ).pack(pady=10)

    def _delete_selected_bill(self):
        """Delete the selected bill."""
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a bill to delete.")
            return

        bill_no = self.history_tree.item(selected[0])["values"][1]

        if messagebox.askyesno("Confirm Delete", f"Delete bill {bill_no}?\nThis cannot be undone."):
            if delete_bill(bill_no):
                self._refresh_history()
                self.status_var.set(f"🗑️ Bill {bill_no} deleted.")
            else:
                messagebox.showerror("Error", "Failed to delete bill.")

    # ══════════════════════════════════════════════════════════════
    # DASHBOARD TAB
    # ══════════════════════════════════════════════════════════════
    def _build_dashboard_tab(self):
        # Stats cards row
        self.stats_frame = tk.Frame(self.dashboard_tab, bg=BG)
        self.stats_frame.pack(fill="x", padx=20, pady=15)

        self.stat_cards = {}
        cards_data = [
            ("total_revenue", "💰 Total Revenue", "$0.00", SUCCESS),
            ("total_bills", "📋 Total Bills", "0", ACCENT),
            ("avg_bill", "📊 Average Bill", "$0.00", WARNING),
        ]

        for i, (key, title, value, color) in enumerate(cards_data):
            card = self._create_stat_card(self.stats_frame, title, value, color)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            self.stat_cards[key] = card
            self.stats_frame.columnconfigure(i, weight=1)

        # Charts row
        charts_frame = tk.Frame(self.dashboard_tab, bg=BG)
        charts_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Left: Revenue chart
        self.revenue_chart_frame = tk.LabelFrame(
            charts_frame, text=" 📈 Monthly Revenue ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY
        )
        self.revenue_chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right: Top items / customers
        right_frame = tk.Frame(charts_frame, bg=BG)
        right_frame.pack(side="right", fill="both", expand=True)

        # Top customers
        self.top_customers_frame = tk.LabelFrame(
            right_frame, text=" 👥 Top Customers ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY
        )
        self.top_customers_frame.pack(fill="both", expand=True, pady=(0, 5))

        # Top items
        self.top_items_frame = tk.LabelFrame(
            right_frame, text=" 🏷️ Top Items ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY
        )
        self.top_items_frame.pack(fill="both", expand=True, pady=(5, 0))

    def _create_stat_card(self, parent, title, value, color):
        """Create a statistics card widget."""
        card = tk.Frame(parent, bg=WHITE, relief="solid", bd=1)

        tk.Label(
            card, text=title,
            font=FONT_SMALL, bg=WHITE, fg=TEXT
        ).pack(pady=(10, 5))

        value_label = tk.Label(
            card, text=value,
            font=FONT_LARGE, bg=WHITE, fg=color
        )
        value_label.pack(pady=(0, 10))
        card.value_label = value_label

        return card

    def _refresh_dashboard(self):
        """Refresh dashboard data and charts."""
        # Update stat cards
        total_revenue = get_total_revenue()
        total_bills = get_total_bills_count()
        avg_bill = get_average_bill_amount()

        self.stat_cards["total_revenue"].value_label.config(text=f"${total_revenue:,.2f}")
        self.stat_cards["total_bills"].value_label.config(text=str(total_bills))
        self.stat_cards["avg_bill"].value_label.config(text=f"${avg_bill:,.2f}")

        # Update charts
        self._update_revenue_chart()
        self._update_top_customers()
        self._update_top_items()

    def _update_revenue_chart(self):
        """Update the revenue chart."""
        # Clear existing content
        for widget in self.revenue_chart_frame.winfo_children():
            widget.destroy()

        monthly_data = get_monthly_revenue(6)

        if not monthly_data:
            tk.Label(
                self.revenue_chart_frame,
                text="No data available",
                font=FONT_LABEL, bg=BG, fg=TEXT
            ).pack(expand=True)
            return

        if CHARTS_AVAILABLE:
            fig = Figure(figsize=(5, 3), dpi=100)
            fig.patch.set_facecolor('#F0F4F8')
            ax = fig.add_subplot(111)

            months = [d[0] for d in monthly_data]
            revenues = [d[1] for d in monthly_data]

            bars = ax.bar(months, revenues, color=ACCENT)
            ax.set_ylabel('Revenue ($)', fontsize=9)
            ax.tick_params(axis='x', rotation=45, labelsize=8)
            ax.tick_params(axis='y', labelsize=8)
            ax.set_facecolor('#F0F4F8')

            for bar, rev in zip(bars, revenues):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        f'${rev:.0f}', ha='center', va='bottom', fontsize=7)

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, self.revenue_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        else:
            # Fallback: text-based display
            tk.Label(
                self.revenue_chart_frame,
                text="(Install matplotlib for charts)",
                font=FONT_SMALL, bg=BG, fg=TEXT
            ).pack(pady=5)

            for month, revenue in monthly_data:
                row = tk.Frame(self.revenue_chart_frame, bg=BG)
                row.pack(fill="x", padx=10, pady=2)
                tk.Label(row, text=month, font=FONT_LABEL, bg=BG, fg=TEXT, width=10).pack(side="left")
                tk.Label(row, text=f"${revenue:,.2f}", font=FONT_BOLD, bg=BG, fg=SUCCESS).pack(side="left")

    def _update_top_customers(self):
        """Update top customers list."""
        for widget in self.top_customers_frame.winfo_children():
            widget.destroy()

        customers = get_top_customers(5)

        if not customers:
            tk.Label(
                self.top_customers_frame,
                text="No data available",
                font=FONT_LABEL, bg=BG, fg=TEXT
            ).pack(expand=True)
            return

        for i, (name, total, count) in enumerate(customers, 1):
            row = tk.Frame(self.top_customers_frame, bg=BG)
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(
                row, text=f"{i}.",
                font=FONT_BOLD, bg=BG, fg=TEXT, width=3
            ).pack(side="left")

            tk.Label(
                row, text=name[:20],
                font=FONT_LABEL, bg=BG, fg=TEXT, width=15, anchor="w"
            ).pack(side="left")

            tk.Label(
                row, text=f"${total:,.2f}",
                font=FONT_BOLD, bg=BG, fg=SUCCESS
            ).pack(side="right")

            tk.Label(
                row, text=f"({count} bills)",
                font=FONT_SMALL, bg=BG, fg=TEXT
            ).pack(side="right", padx=5)

    def _update_top_items(self):
        """Update top items list."""
        for widget in self.top_items_frame.winfo_children():
            widget.destroy()

        items = get_top_items(5)

        if not items:
            tk.Label(
                self.top_items_frame,
                text="No data available",
                font=FONT_LABEL, bg=BG, fg=TEXT
            ).pack(expand=True)
            return

        for i, (name, qty, revenue) in enumerate(items, 1):
            row = tk.Frame(self.top_items_frame, bg=BG)
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(
                row, text=f"{i}.",
                font=FONT_BOLD, bg=BG, fg=TEXT, width=3
            ).pack(side="left")

            tk.Label(
                row, text=name[:20],
                font=FONT_LABEL, bg=BG, fg=TEXT, width=15, anchor="w"
            ).pack(side="left")

            tk.Label(
                row, text=f"${revenue:,.2f}",
                font=FONT_BOLD, bg=BG, fg=SUCCESS
            ).pack(side="right")

            tk.Label(
                row, text=f"(×{qty})",
                font=FONT_SMALL, bg=BG, fg=TEXT
            ).pack(side="right", padx=5)

    # ══════════════════════════════════════════════════════════════
    # STATUS BAR
    # ══════════════════════════════════════════════════════════════
    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="✅ Ready — Add items and generate a receipt.")
        tk.Label(
            self, textvariable=self.status_var,
            font=FONT_SMALL, bg=PRIMARY, fg=WHITE,
            anchor="w", padx=10
        ).pack(fill="x", side="bottom")

    # ══════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════
    def _label(self, parent, text):
        return tk.Label(parent, text=text, font=FONT_BOLD, bg=BG, fg=TEXT)

    def _entry(self, parent, textvariable, width=20):
        return tk.Entry(
            parent, textvariable=textvariable,
            font=FONT_LABEL, width=width,
            relief="solid", bd=1
        )

    @staticmethod
    def _generate_bill_no():
        return "BILL-" + datetime.now().strftime("%Y%m%d%H%M%S")

    def _update_total(self):
        tax = self._get_tax_rate()
        subtotal = sum(i["subtotal"] for i in self.items)
        total = subtotal + subtotal * tax
        symbol = get_symbol(self.current_currency)
        self.total_var.set(f"Total: {symbol}{total:.2f}  (incl. {tax*100:.0f}% tax)")

    def _get_tax_rate(self):
        try:
            return float(self.tax_var.get()) / 100
        except ValueError:
            return 0.0

    # ══════════════════════════════════════════════════════════════
    # ITEM ACTIONS
    # ══════════════════════════════════════════════════════════════
    def _add_item(self):
        name = self.item_name_var.get().strip()
        qty_s = self.qty_var.get().strip()
        prc_s = self.price_var.get().strip()

        if not name:
            return messagebox.showwarning("Missing Field", "Please enter an item name.")
        try:
            qty = int(qty_s)
            price = float(prc_s)
            if qty <= 0 or price < 0:
                raise ValueError
        except ValueError:
            return messagebox.showerror("Invalid Input", "Quantity must be a positive integer and price a positive number.")

        subtotal = qty * price
        item = {"name": name, "qty": qty, "price": price, "subtotal": subtotal}
        self.items.append(item)

        symbol = get_symbol(self.current_currency)
        idx = len(self.items)
        self.tree.insert("", "end", values=(
            idx, name, qty, f"{symbol}{price:.2f}", f"{symbol}{subtotal:.2f}"
        ))

        self.item_name_var.set("")
        self.qty_var.set("1")
        self.price_var.set("0.00")
        self._update_total()
        self.status_var.set(f"✅ Item '{name}' added.")

    def _remove_item(self):
        selected = self.tree.selection()
        if not selected:
            return messagebox.showwarning("No Selection", "Please select an item to remove.")

        for sel in selected:
            idx = int(self.tree.item(sel)["values"][0]) - 1
            self.items.pop(idx)
            self.tree.delete(sel)

        # Refresh numbering
        symbol = get_symbol(self.current_currency)
        for i, row_id in enumerate(self.tree.get_children()):
            item = self.items[i]
            self.tree.item(row_id, values=(
                i + 1,
                item["name"],
                item["qty"],
                f"{symbol}{item['price']:.2f}",
                f"{symbol}{item['subtotal']:.2f}"
            ))

        self._update_total()
        self.status_var.set("🗑️ Item removed.")

    def _clear_all(self):
        if not self.items:
            return
        if messagebox.askyesno("Clear All", "Remove all items from the list?"):
            self.items.clear()
            for row in self.tree.get_children():
                self.tree.delete(row)
            self._update_total()
            self.status_var.set("🔄 All items cleared.")

    # ══════════════════════════════════════════════════════════════
    # SAVE & GENERATE
    # ══════════════════════════════════════════════════════════════
    def _save_and_generate(self):
        bill_no = self.bill_no_var.get().strip()
        customer = self.customer_var.get().strip()
        tax = self._get_tax_rate()
        currency = self.currency_var.get()

        if not customer:
            return messagebox.showwarning("Missing Field", "Please enter the customer name.")
        if not self.items:
            return messagebox.showwarning("No Items", "Please add at least one item.")

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.status_var.set("⏳ Generating receipt...")
        self.update_idletasks()

        file_path, grand_total, items_with_sub = generate_receipt(
            bill_no, customer, self.items.copy(), tax, currency
        )

        saved = save_bill(bill_no, customer, date_str, items_with_sub, grand_total, currency)

        if saved:
            symbol = get_symbol(currency)
            self.status_var.set(f"✅ Receipt saved → {file_path}")
            if messagebox.askyesno(
                "Success! 🎉",
                f"Receipt generated!\nTotal: {symbol}{grand_total:.2f} ({currency})\n\nOpen the PDF now?"
            ):
                self._open_file(file_path)

            self._clear_all()
            self.bill_no_var.set(self._generate_bill_no())
            self.customer_var.set("")
        else:
            messagebox.showerror("Error", f"Bill No '{bill_no}' already exists in the database!")

    @staticmethod
    def _open_file(path):
        """Open the PDF with the default system viewer."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Open Error", str(e))


# ── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    app = BillApp()
    app.mainloop()
