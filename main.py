import tkinter as tk
from tkinter import ttk, messagebox
import os, subprocess, sys
from datetime import datetime

from database import init_db, save_bill
from receipt_generator import generate_receipt

# ── Colour Palette ───────────────────────────────────────────
BG        = "#F0F4F8"
PRIMARY   = "#2C3E50"
ACCENT    = "#3498DB"
SUCCESS   = "#27AE60"
DANGER    = "#E74C3C"
WHITE     = "#FFFFFF"
LIGHT     = "#ECF0F1"
TEXT      = "#2C3E50"

FONT_TITLE  = ("Helvetica", 20, "bold")
FONT_LABEL  = ("Helvetica", 11)
FONT_BOLD   = ("Helvetica", 11, "bold")
FONT_SMALL  = ("Helvetica",  9)
FONT_BUTTON = ("Helvetica", 11, "bold")


class BillApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧾 Bill Receipt Generator")
        self.geometry("900x680")
        self.resizable(True, True)
        self.configure(bg=BG)

        init_db()
        self.items = []          # list of item dicts
        self._build_ui()

    # ── UI Builder ───────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_form()
        self._build_items_section()
        self._build_buttons()
        self._build_status_bar()

    # ── Header ───────────────────────────────────────────────
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

    # ── Customer & Bill Info Form ────────────────────────────
    def _build_form(self):
        frame = tk.LabelFrame(
            self, text=" 📋 Bill Information ",
            font=FONT_BOLD, bg=BG, fg=PRIMARY,
            padx=10, pady=10
        )
        frame.pack(fill="x", padx=20, pady=(15, 5))

        # Row 1
        row1 = tk.Frame(frame, bg=BG)
        row1.pack(fill="x", pady=4)

        self._label(row1, "Bill No:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.bill_no_var = tk.StringVar(value=self._generate_bill_no())
        self._entry(row1, self.bill_no_var, width=20).grid(row=0, column=1, padx=(0, 20))

        self._label(row1, "Customer Name:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.customer_var = tk.StringVar()
        self._entry(row1, self.customer_var, width=30).grid(row=0, column=3, padx=(0, 20))

        self._label(row1, "Tax (%):").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.tax_var = tk.StringVar(value="0")
        self._entry(row1, self.tax_var, width=8).grid(row=0, column=5)

    # ── Items Section ────────────────────────────────────────
    def _build_items_section(self):
        # ── Input row for adding items ──
        add_frame = tk.LabelFrame(
            self, text=" ➕ Add Item ",
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

        self._label(row, "Unit Price ($):").grid(row=0, column=4, sticky="w", padx=(0, 5))
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
        tree_frame = tk.Frame(self, bg=BG)
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

        # Style the treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=WHITE, foreground=TEXT,
                         rowheight=28, fieldbackground=WHITE, font=FONT_LABEL)
        style.configure("Treeview.Heading",
                         background=PRIMARY, foreground=WHITE,
                         font=FONT_BOLD, relief="flat")
        style.map("Treeview", background=[("selected", ACCENT)])

        # Total label
        self.total_var = tk.StringVar(value="Total: \$0.00")
        tk.Label(
            self, textvariable=self.total_var,
            font=("Helvetica", 13, "bold"),
            bg=BG, fg=DANGER
        ).pack(anchor="e", padx=25)

    # ── Action Buttons ───────────────────────────────────────
    def _build_buttons(self):
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=20, pady=10)

        buttons = [
            ("🗑️  Remove Selected", DANGER,   self._remove_item),
            ("🔄  Clear All",        "#7F8C8D", self._clear_all),
            ("💾  Save & Generate",  SUCCESS,   self._save_and_generate),
        ]
        for text, color, cmd in buttons:
            tk.Button(
                btn_frame, text=text,
                font=FONT_BUTTON, bg=color, fg=WHITE,
                relief="flat", cursor="hand2",
                padx=15, pady=8,
                command=cmd
            ).pack(side="right", padx=5)

    # ── Status Bar ───────────────────────────────────────────
    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="✅ Ready — Add items and generate a receipt.")
        tk.Label(
            self, textvariable=self.status_var,
            font=FONT_SMALL, bg=PRIMARY, fg=WHITE,
            anchor="w", padx=10
        ).pack(fill="x", side="bottom")

    # ── Helpers ──────────────────────────────────────────────
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
        self.total_var.set(f"Total: ${total:.2f}  (incl. {tax*100:.0f}% tax)")

    def _get_tax_rate(self):
        try:
            return float(self.tax_var.get()) / 100
        except ValueError:
            return 0.0

    # ── Item Actions ─────────────────────────────────────────
    def _add_item(self):
        name  = self.item_name_var.get().strip()
        qty_s = self.qty_var.get().strip()
        prc_s = self.price_var.get().strip()

        if not name:
            return messagebox.showwarning("Missing Field", "Please enter an item name.")
        try:
            qty   = int(qty_s)
            price = float(prc_s)
            if qty <= 0 or price < 0:
                raise ValueError
        except ValueError:
            return messagebox.showerror("Invalid Input", "Quantity must be a positive integer and price a positive number.")

        subtotal = qty * price
        item = {"name": name, "qty": qty, "price": price, "subtotal": subtotal}
        self.items.append(item)

        idx = len(self.items)
        self.tree.insert("", "end", values=(
            idx, name, qty, f"${price:.2f}", f"${subtotal:.2f}"
        ))

        # Reset input fields
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
        for i, row_id in enumerate(self.tree.get_children(), start=1):
            vals = list(self.tree.item(row_id)["values"])
            vals[0] = i
            self.tree.item(row_id, values=vals)

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

    # ── Save & Generate ──────────────────────────────────────
    def _save_and_generate(self):
        bill_no  = self.bill_no_var.get().strip()
        customer = self.customer_var.get().strip()
        tax      = self._get_tax_rate()

        if not customer:
            return messagebox.showwarning("Missing Field", "Please enter the customer name.")
        if not self.items:
            return messagebox.showwarning("No Items", "Please add at least one item.")

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate PDF
        self.status_var.set("⏳ Generating receipt...")
        self.update_idletasks()

        file_path, grand_total, items_with_sub = generate_receipt(
            bill_no, customer, self.items.copy(), tax
        )

        # Save to DB
        saved = save_bill(bill_no, customer, date_str, items_with_sub, grand_total)

        if saved:
            self.status_var.set(f"✅ Receipt saved → {file_path}")
            if messagebox.askyesno(
                "Success! 🎉",
                f"Receipt generated!\nTotal: ${grand_total:.2f}\n\nOpen the PDF now?"
            ):
                self._open_file(file_path)

            # Reset for next bill
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