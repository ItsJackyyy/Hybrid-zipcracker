import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import zipfile
import time
import os
import threading
import itertools
import string

# --- VS Code-like color palette ---
VS_BG = '#1e1e1e'           # Editor background
VS_PANEL = '#252526'        # Side panel
VS_ACCENT = '#007acc'       # Blue accent
VS_TEXT = "#ffffff"         # Main text
VS_INPUT_BG = '#2d2d2d'     # Input fields
VS_GREEN = '#4ec9b0'        # Success/green
VS_RED = '#f44747'          # Error/red
VS_BORDER = '#333333'       # Borders
VS_FONT = ('Consolas', 11)
VS_FONT_BOLD = ('Consolas', 11, 'bold')

# --- Helper: Preview a file's contents (text or binary) ---


def preview_file(path, filename):
    if not os.path.exists(path):
        return f"❌ File not found: {path}\n"
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            content = f.read(500)
            msg = f"\n--- {filename} (text) ---\n" + content.strip()
            if len(content) == 500:
                msg += "\n... [truncated]"
            return msg + "\n"
    except Exception:
        try:
            with open(path, "rb") as f:
                content = f.read(64)
                msg = f"\n--- {filename} (binary) ---\nSize: {os.path.getsize(path)} bytes\nHex preview: {content.hex(' ', 1).upper()}"
                return msg + "\n"
        except Exception as e:
            return f"❌ Could not preview {filename}: {e}\n"

# --- Brute-force password generator ---


def brute_force_passwords(charset, min_len, max_len):
    for length in range(min_len, max_len + 1):
        for pw_tuple in itertools.product(charset, repeat=length):
            yield ''.join(pw_tuple)

# --- Recursively crack nested ZIPs ---


def handle_nested_zip(zip_path, wordlist, output, stop_flag, on_password_found, mode, bf_opts, indent=1):
    output(f"{'  '*indent}🔁 Attempting to crack nested ZIP: {zip_path}\n")
    crack_zip(zip_path, wordlist, os.path.splitext(zip_path)[
              0], output, stop_flag, on_password_found, mode, bf_opts, indent=indent+1)

# --- Main cracking logic ---


def crack_zip(zip_path, wordlist, extract_to, output, stop_flag, on_password_found, mode, bf_opts, indent=0):
    found = False
    extracted_files = []
    start_time = time.time()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            output(f"{'  '*indent}📂 Files in the ZIP: {zip_path}\n")
            for name in zf.namelist():
                output(f"{'  '*indent}- {name}\n")
            # --- Dictionary attack ---
            if mode in ("Auto", "Dictionary") and wordlist:
                for count, word in enumerate(wordlist, 1):
                    if stop_flag() or found:
                        output(f"{'  '*indent}⏹️ Stopped by user.\n")
                        return
                    output(
                        f"{'  '*indent}Attempt {count}: Trying password → {word}\n")
                    try:
                        zf.extractall(path=extract_to,
                                      pwd=word.encode("utf-8"))
                        elapsed = time.time() - start_time
                        output(
                            f"{'  '*indent}✅ Password found: {word}\n{'  '*indent}⏱️ Time taken: {elapsed:.2f} seconds\n")
                        found = True
                        on_password_found(word)
                        output(f"{'  '*indent}🔎 Previewing extracted files:\n")
                        for file in zf.namelist():
                            full_path = os.path.join(extract_to, file)
                            file_dir = os.path.dirname(full_path)
                            if file_dir and not os.path.exists(file_dir):
                                os.makedirs(file_dir, exist_ok=True)
                            if os.path.isdir(full_path) or file in extracted_files:
                                continue
                            extracted_files.append(file)
                            if file.lower().endswith(".zip"):
                                handle_nested_zip(
                                    full_path, wordlist, output, stop_flag, on_password_found, mode, bf_opts, indent=indent+1)
                            else:
                                output(preview_file(full_path, file))
                        break
                    except Exception:
                        continue
            # --- Brute-force attack (if not found or selected) ---
            if not found and (mode in ("Auto", "Brute Force")):
                charset = bf_opts['charset']
                min_len = bf_opts['min_len']
                max_len = bf_opts['max_len']
                output(
                    f"{'  '*indent}🔨 Starting brute-force: charset=[{charset}], length={min_len}-{max_len}\n")
                for count, word in enumerate(brute_force_passwords(charset, min_len, max_len), 1):
                    if stop_flag() or found:
                        output(f"{'  '*indent}⏹️ Stopped by user.\n")
                        return
                    output(
                        f"{'  '*indent}Brute {count}: Trying password → {word}\n")
                    try:
                        zf.extractall(path=extract_to,
                                      pwd=word.encode("utf-8"))
                        elapsed = time.time() - start_time
                        output(
                            f"{'  '*indent}✅ Password found: {word}\n{'  '*indent}⏱️ Time taken: {elapsed:.2f} seconds\n")
                        found = True
                        on_password_found(word)
                        output(f"{'  '*indent}🔎 Previewing extracted files:\n")
                        for file in zf.namelist():
                            full_path = os.path.join(extract_to, file)
                            file_dir = os.path.dirname(full_path)
                            if file_dir and not os.path.exists(file_dir):
                                os.makedirs(file_dir, exist_ok=True)
                            if os.path.isdir(full_path) or file in extracted_files:
                                continue
                            extracted_files.append(file)
                            if file.lower().endswith(".zip"):
                                handle_nested_zip(
                                    full_path, wordlist, output, stop_flag, on_password_found, mode, bf_opts, indent=indent+1)
                            else:
                                output(preview_file(full_path, file))
                        break
                    except Exception:
                        continue
    except Exception as e:
        output(f"{'  '*indent}❌ Could not open ZIP file {zip_path}: {e}\n")
        return
    elapsed = time.time() - start_time
    if not found and not stop_flag():
        output(f"{'  '*indent}❌ Password not found in dictionary or brute-force.\n")
    output(f"{'  '*indent}⏱️ Total time elapsed: {elapsed:.2f} seconds\n\n")

# --- GUI Application ---


class ZipCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZIP Cracker GUI + Chatbot (VS Code Style)")
        self.root.geometry("1150x700")
        self.root.minsize(950, 500)
        self.stop_cracking = False
        self.cracking_thread = None

        # --- Main container frame ---
        main_frame = tk.Frame(root, bg=VS_BG)
        main_frame.pack(fill='both', expand=True)

        # --- Left: ZIP Cracker Section ---
        left_frame = tk.Frame(main_frame, bg=VS_BG)
        left_frame.pack(side='left', fill='both', expand=True)

        # --- File selection ---
        frm = tk.Frame(left_frame, bg=VS_BG)
        frm.pack(pady=5, anchor='nw')
        tk.Label(frm, text="ZIP File:", fg=VS_TEXT, bg=VS_BG,
                 font=VS_FONT).grid(row=0, column=0, sticky="e")
        self.zip_entry = tk.Entry(
            frm, width=40, bg=VS_INPUT_BG, fg=VS_TEXT, insertbackground=VS_TEXT, font=VS_FONT)
        self.zip_entry.grid(row=0, column=1, padx=5)
        tk.Button(frm, text="Browse", command=self.browse_zip, bg=VS_ACCENT, fg='white',
                  font=VS_FONT_BOLD, activebackground=VS_PANEL).grid(row=0, column=2)

        tk.Label(frm, text="Wordlist:", fg=VS_TEXT, bg=VS_BG,
                 font=VS_FONT).grid(row=1, column=0, sticky="e")
        self.wordlist_entry = tk.Entry(
            frm, width=40, bg=VS_INPUT_BG, fg=VS_TEXT, insertbackground=VS_TEXT, font=VS_FONT)
        self.wordlist_entry.grid(row=1, column=1, padx=5)
        tk.Button(frm, text="Browse", command=self.browse_wordlist, bg=VS_ACCENT,
                  fg='white', font=VS_FONT_BOLD, activebackground=VS_PANEL).grid(row=1, column=2)

        # --- Mode selector ---
        mode_frame = tk.Frame(left_frame, bg=VS_BG)
        mode_frame.pack(pady=(5, 0), anchor='nw')
        tk.Label(mode_frame, text="Mode:", fg=VS_TEXT,
                 bg=VS_BG, font=VS_FONT).pack(side='left')
        self.mode_var = tk.StringVar(value="Auto")
        tk.Radiobutton(mode_frame, text="Auto (Recommended)", variable=self.mode_var, value="Auto", bg=VS_BG,
                       fg=VS_TEXT, selectcolor=VS_PANEL, font=VS_FONT, activebackground=VS_BG).pack(side='left', padx=5)
        tk.Radiobutton(mode_frame, text="Dictionary", variable=self.mode_var, value="Dictionary", bg=VS_BG,
                       fg=VS_TEXT, selectcolor=VS_PANEL, font=VS_FONT, activebackground=VS_BG).pack(side='left', padx=5)
        tk.Radiobutton(mode_frame, text="Brute Force", variable=self.mode_var, value="Brute Force", bg=VS_BG,
                       fg=VS_TEXT, selectcolor=VS_PANEL, font=VS_FONT, activebackground=VS_BG).pack(side='left', padx=5)

        # --- Brute-force options ---
        bf_opts_frame = tk.Frame(left_frame, bg=VS_BG)
        bf_opts_frame.pack(pady=(2, 0), anchor='nw')
        tk.Label(bf_opts_frame, text="Charset:", fg=VS_TEXT, bg=VS_BG,
                 font=VS_FONT).grid(row=0, column=0, sticky='e')
        self.charset_var = tk.StringVar(value=string.ascii_lowercase)
        charset_entry = tk.Entry(bf_opts_frame, textvariable=self.charset_var, width=20,
                                 bg=VS_INPUT_BG, fg=VS_TEXT, insertbackground=VS_TEXT, font=VS_FONT)
        charset_entry.grid(row=0, column=1, padx=2)
        tk.Label(bf_opts_frame, text="Min Length:", fg=VS_TEXT,
                 bg=VS_BG, font=VS_FONT).grid(row=0, column=2, sticky='e')
        self.minlen_var = tk.IntVar(value=1)
        tk.Entry(bf_opts_frame, textvariable=self.minlen_var, width=3, bg=VS_INPUT_BG,
                 fg=VS_TEXT, insertbackground=VS_TEXT, font=VS_FONT).grid(row=0, column=3, padx=2)
        tk.Label(bf_opts_frame, text="Max Length:", fg=VS_TEXT,
                 bg=VS_BG, font=VS_FONT).grid(row=0, column=4, sticky='e')
        self.maxlen_var = tk.IntVar(value=4)
        tk.Entry(bf_opts_frame, textvariable=self.maxlen_var, width=3, bg=VS_INPUT_BG,
                 fg=VS_TEXT, insertbackground=VS_TEXT, font=VS_FONT).grid(row=0, column=5, padx=2)
        # Show/hide brute-force options based on mode

        def update_bf_opts(*args):
            if self.mode_var.get() == "Brute Force":
                bf_opts_frame.pack(pady=(2, 0), anchor='nw')
            else:
                bf_opts_frame.pack_forget()
        self.mode_var.trace_add('write', update_bf_opts)
        update_bf_opts()

        # --- Start/Stop buttons ---
        btn_frame = tk.Frame(left_frame, bg=VS_BG)
        btn_frame.pack(pady=5, anchor='nw')
        self.start_btn = tk.Button(btn_frame, text="Start Cracking", command=self.start_cracking,
                                   bg=VS_ACCENT, fg='white', font=VS_FONT_BOLD, activebackground=VS_PANEL)
        self.start_btn.pack(side='left', padx=(0, 10))
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_cracking_func,
                                  bg=VS_RED, fg='white', font=VS_FONT_BOLD, state='disabled', activebackground=VS_PANEL)
        self.stop_btn.pack(side='left')

        # --- Output area ---
        tk.Label(left_frame, text="Progress & Results:", fg=VS_ACCENT,
                 bg=VS_BG, font=VS_FONT_BOLD).pack(anchor='nw')
        self.output_area = scrolledtext.ScrolledText(left_frame, width=65, height=28, state='disabled',
                                                     font=VS_FONT, bg=VS_PANEL, fg=VS_TEXT, insertbackground=VS_TEXT, borderwidth=2, relief='flat')
        self.output_area.pack(padx=2, pady=5, fill='both', expand=True)

        # --- Right: Chatbot Section ---
        chat_frame = tk.Frame(main_frame, padx=10, pady=10,
                              bg=VS_PANEL, relief='groove', bd=2)
        chat_frame.pack(side='right', fill='y')
        chat_frame.pack_propagate(False)
        chat_frame.config(width=350)

        tk.Label(chat_frame, text="Chatbot (Llama LLM Ready)", font=VS_FONT_BOLD,
                 bg=VS_PANEL, fg=VS_ACCENT).pack(anchor='nw', pady=(0, 5))

        # --- Chat history area ---
        self.chat_history = scrolledtext.ScrolledText(chat_frame, width=40, height=25, state='disabled', font=(
            "Segoe UI", 10), bg=VS_BG, fg=VS_TEXT, insertbackground=VS_TEXT, borderwidth=2, relief='flat')
        self.chat_history.pack(padx=2, pady=5, fill='both', expand=True)

        # --- Chat input bar ---
        input_frame = tk.Frame(chat_frame, bg=VS_PANEL)
        input_frame.pack(fill='x', pady=(5, 0))
        self.chat_entry = tk.Entry(input_frame, width=28, font=(
            "Segoe UI", 10), bg=VS_INPUT_BG, fg=VS_TEXT, insertbackground=VS_TEXT)
        self.chat_entry.pack(side='left', padx=(
            0, 5), pady=2, fill='x', expand=True)
        self.chat_entry.bind('<Return>', self.send_chat)
        tk.Button(input_frame, text="Send", command=self.send_chat, bg=VS_ACCENT, fg='white',
                  font=VS_FONT_BOLD, activebackground=VS_PANEL).pack(side='left', pady=2)

    # --- ZIP Cracker methods ---
    def browse_zip(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if path:
            self.zip_entry.delete(0, tk.END)
            self.zip_entry.insert(0, path)

    def browse_wordlist(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self.wordlist_entry.delete(0, tk.END)
            self.wordlist_entry.insert(0, path)

    def print_output(self, text):
        self.output_area.configure(state='normal')
        self.output_area.insert(tk.END, text)
        self.output_area.see(tk.END)
        self.output_area.configure(state='disabled')
        self.root.update()

    def start_cracking(self):
        zip_path = self.zip_entry.get().strip()
        wordlist_path = self.wordlist_entry.get().strip()
        mode = self.mode_var.get()
        bf_opts = {
            'charset': self.charset_var.get(),
            'min_len': self.minlen_var.get(),
            'max_len': self.maxlen_var.get()
        }
        if not os.path.isfile(zip_path):
            messagebox.showerror("Error", "Please select a valid ZIP file.")
            return
        if mode in ("Auto", "Dictionary") and not os.path.isfile(wordlist_path):
            messagebox.showerror(
                "Error", "Please select a valid wordlist file.")
            return
        self.output_area.configure(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.configure(state='disabled')
        self.stop_cracking = False
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.cracking_thread = threading.Thread(target=self.run_cracker, args=(
            zip_path, wordlist_path, mode, bf_opts), daemon=True)
        self.cracking_thread.start()

    def stop_cracking_func(self):
        self.stop_cracking = True
        self.stop_btn.config(state='disabled')
        self.start_btn.config(state='normal')

    def run_cracker(self, zip_path, wordlist_path, mode, bf_opts):
        wordlist = []
        if mode in ("Auto", "Dictionary"):
            try:
                with open(wordlist_path, encoding="utf-8", errors="ignore") as f:
                    wordlist = [line.strip() for line in f if line.strip()]
            except Exception as e:
                self.print_output(f"❌ Could not read wordlist: {e}\n")
                self.stop_btn.config(state='disabled')
                self.start_btn.config(state='normal')
                return
        crack_zip(
            zip_path, wordlist, extract_to="_extracted", output=self.print_output,
            stop_flag=lambda: self.stop_cracking, on_password_found=self.show_password_popup,
            mode=mode, bf_opts=bf_opts
        )
        self.stop_btn.config(state='disabled')
        self.start_btn.config(state='normal')

    def show_password_popup(self, password):
        # Show a popup with the password highlighted in green
        popup = tk.Toplevel(self.root)
        popup.title("Password Found!")
        popup.configure(bg=VS_BG)
        popup.geometry("350x120")
        popup.resizable(False, False)
        tk.Label(popup, text="Password Found!", font=VS_FONT_BOLD,
                 fg=VS_GREEN, bg=VS_BG).pack(pady=(18, 5))
        pw_label = tk.Label(popup, text=password, font=(
            "Consolas", 16, "bold"), fg=VS_BG, bg=VS_GREEN, padx=12, pady=6)
        pw_label.pack(pady=(0, 10))
        tk.Button(popup, text="OK", command=popup.destroy, bg=VS_ACCENT, fg='white',
                  font=VS_FONT_BOLD, activebackground=VS_PANEL).pack(pady=(0, 10))
        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)

    # --- Chatbot methods ---
    def send_chat(self, event=None):
        user_msg = self.chat_entry.get().strip()
        if not user_msg:
            return
        self.append_chat("You", user_msg)
        self.chat_entry.delete(0, tk.END)
        # Placeholder: Here you would call your Llama LLM API and get a response
        # For now, just echo the message with a placeholder response
        threading.Thread(target=self.fake_llm_response,
                         args=(user_msg,), daemon=True).start()

    def append_chat(self, sender, message):
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, f"{sender}: {message}\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state='disabled')

    def fake_llm_response(self, user_msg):
        # Simulate a delay and echo the message as a placeholder
        time.sleep(0.7)
        response = f"[Llama LLM placeholder] You said: {user_msg}"
        self.append_chat("Llama", response)


if __name__ == "__main__":
    root = tk.Tk()
    app = ZipCrackerApp(root)
    root.mainloop()
