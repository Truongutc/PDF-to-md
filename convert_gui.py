import os
import sys
import threading
import winreg
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# Refresh PATH from registry so the script can locate 'java' immediately
# even if the system environment variables were changed recently.
def refresh_path():
    try:
        # System Path
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
        # User Path
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            user_path = ""
        
        # Combine and apply
        combined = sys_path
        if user_path:
            combined += ";" + user_path
        os.environ["PATH"] = combined
    except Exception as e:
        print(f"Error refreshing PATH: {e}")

refresh_path()

try:
    import opendataloader_pdf
except ImportError:
    messagebox.showerror("Lỗi", "Không tìm thấy thư viện 'opendataloader-pdf'. Vui lòng cài đặt bằng cách chạy lệnh: pip install opendataloader-pdf")
    sys.exit(1)


class AppRedirector:
    """Redirects stdout/stderr to the text widget in the GUI."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

    def flush(self):
        pass


class PDFToMarkdownGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenDataLoader PDF to Markdown Converter")
        self.root.geometry("680x520")
        self.root.minsize(600, 450)
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('vista')  # Native Windows theme
        
        self.selected_files = []
        self.output_dir = ""
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main Frame with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title Label
        title_label = ttk.Label(
            main_frame, 
            text="Chuyển đổi tài liệu PDF sang Markdown", 
            font=("Segoe UI", 14, "bold"),
            foreground="#1e3d59"
        )
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # --- File Selection Frame ---
        file_frame = ttk.LabelFrame(main_frame, text=" 1. Chọn file PDF cần chuyển đổi ", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_entry = ttk.Entry(file_frame, font=("Segoe UI", 9))
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.file_entry.insert(0, "Chưa chọn file nào...")
        self.file_entry.configure(state='readonly')
        
        browse_file_btn = ttk.Button(file_frame, text="Chọn file PDF...", command=self.browse_files)
        browse_file_btn.pack(side=tk.RIGHT)
        
        # --- Output Folder Frame ---
        folder_frame = ttk.LabelFrame(main_frame, text=" 2. Chọn thư mục lưu file kết quả (.md) ", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.folder_entry = ttk.Entry(folder_frame, font=("Segoe UI", 9))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_entry.insert(0, "Mặc định (Lưu cùng thư mục với file gốc)")
        self.folder_entry.configure(state='readonly')
        
        browse_folder_btn = ttk.Button(folder_frame, text="Chọn thư mục...", command=self.browse_folder)
        browse_folder_btn.pack(side=tk.RIGHT)
        
        # --- Control & Progress Frame ---
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(
            control_frame, 
            text="BẮT ĐẦU CHUYỂN ĐỔI", 
            command=self.start_conversion_thread,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # --- Log Output Frame ---
        log_frame = ttk.LabelFrame(main_frame, text=" Tiến trình xử lý (Logs) ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = ScrolledText(
            log_frame, 
            height=12, 
            state='disabled', 
            font=("Consolas", 9), 
            bg="#f8f9fa", 
            fg="#2d3748"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Redirect sys.stdout to our log window
        sys.stdout = AppRedirector(self.log_text)
        sys.stderr = AppRedirector(self.log_text)
        
    def browse_files(self):
        files = filedialog.askopenfilenames(
            title="Chọn các file PDF",
            filetypes=[("Tài liệu PDF", "*.pdf")]
        )
        if files:
            self.selected_files = list(files)
            self.file_entry.configure(state='normal')
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, f"Đã chọn {len(self.selected_files)} file: " + ", ".join([os.path.basename(f) for f in self.selected_files]))
            self.file_entry.configure(state='readonly')
            print(f"[Hệ thống] Đã chọn {len(self.selected_files)} file PDF để xử lý.")
            
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục lưu file Markdown")
        if folder:
            self.output_dir = folder
            self.folder_entry.configure(state='normal')
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, self.output_dir)
            self.folder_entry.configure(state='readonly')
            print(f"[Hệ thống] Thư mục lưu kết quả: {self.output_dir}")

    def start_conversion_thread(self):
        if not self.selected_files:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một file PDF trước khi bắt đầu!")
            return
            
        # Disable buttons while running
        self.start_btn.configure(state='disabled')
        self.progress.start(10)
        
        # Start conversion in a background thread to prevent UI freezing
        thread = threading.Thread(target=self.run_conversion)
        thread.daemon = True
        thread.start()
        
    def run_conversion(self):
        try:
            print("\n" + "="*50)
            print("[Bắt đầu] Đang chuẩn bị chuyển đổi tài liệu...")
            
            output_folder = self.output_dir if self.output_dir else None
            
            # Run the parser converter
            opendataloader_pdf.convert(
                input_path=self.selected_files,
                output_dir=output_folder,
                format="markdown"
            )
            
            print("\n[Hoàn tất] Quá trình chuyển đổi đã hoàn thành thành công!")
            print(f"[Kết quả] Các file Markdown (.md) đã được lưu tại: {output_folder if output_folder else 'Cùng thư mục với file gốc'}")
            print("="*50 + "\n")
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo("Thành công", f"Đã chuyển đổi thành công {len(self.selected_files)} file PDF sang Markdown!"))
            
        except Exception as e:
            print(f"\n[Lỗi] Đã xảy ra lỗi trong quá trình xử lý: {e}\n")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {str(e)}"))
            
        finally:
            # Re-enable buttons and stop progress bar
            self.root.after(0, self.reset_ui)
            
    def reset_ui(self):
        self.start_btn.configure(state='normal')
        self.progress.stop()


if __name__ == "__main__":
    # Create the root window
    root = tk.Tk()
    app = PDFToMarkdownGUI(root)
    root.mainloop()
