
import time
import customtkinter as ctk


def _fmt(s):
	s = int(s)
	return f"{s // 60:02d}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


class ProgressDialog(ctk.CTkToplevel):
	def __init__(self, master, total=None, desc="Working…", unit="it",
				 mininterval=0.1, cancellable=True):
		super().__init__(master)
		self.title(desc)
		self.geometry("420x150")
		self.resizable(False, False)
		self.transient(master)
		self.protocol("WM_DELETE_WINDOW", self.cancel)

		self.total, self.n, self.unit = total, 0, unit
		self.mininterval = mininterval
		self.cancelled = False
		self._t0 = time.perf_counter()
		self._last = 0.0

		self.desc_lbl = ctk.CTkLabel(self, text=desc, anchor="w")
		self.desc_lbl.pack(fill="x", padx=20, pady=(18, 4))

		self.bar = ctk.CTkProgressBar(self)
		self.bar.pack(fill="x", padx=20)
		if total:
			self.bar.set(0)
		else:
			self.bar.configure(mode="indeterminate")
			self.bar.start()

		self.stats_lbl = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=12))
		self.stats_lbl.pack(fill="x", padx=20, pady=4)

		if cancellable:
			ctk.CTkButton(self, text="Cancel", width=80, command=self.cancel).pack(pady=(0, 10))

		self.after(100, self.grab_set)  # CTkToplevel needs the delay, especially on Linux
		self._refresh()

	# --- tqdm-like API ---
	def update(self, n=1, force=False):
		self.n += n
		now = time.perf_counter()
		if not force and now - self._last < self.mininterval and self.n != self.total:
			return
		self._last = now
		self._refresh()
		super().update()		  # pump the Tk event loop so the UI stays responsive

	def set_description(self, text):
		self.desc_lbl.configure(text=text)

	def cancel(self):
		self.cancelled = True

	def close(self):
		if self.winfo_exists():
			self.grab_release()
			self.destroy()

	def __enter__(self):
		return self

	def __exit__(self, *exc):
		self.close()

	# --- internals ---
	def _refresh(self):
		elapsed = time.perf_counter() - self._t0
		rate = self.n / elapsed if elapsed > 0 else 0
		if self.total:
			self.bar.set(self.n / self.total)
			eta = (self.total - self.n) / rate if rate else 0
			txt = f"{self.n}/{self.total}  [{_fmt(elapsed)}<{_fmt(eta)}, {rate:.1f} {self.unit}/s]"
		else:
			txt = f"{self.n}  [{_fmt(elapsed)}, {rate:.1f} {self.unit}/s]"
		self.stats_lbl.configure(text=txt)


