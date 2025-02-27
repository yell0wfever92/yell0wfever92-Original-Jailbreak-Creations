import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import re
from datetime import datetime
from rapidfuzz import fuzz  # Ensure you have installed rapidfuzz via pip

class ChatGPTSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("ChatGPT Conversation Search")

        self.conversations = []  # Will hold your conversations
        
        # Button to load the conversation export file
        self.load_button = tk.Button(master, text="Load ChatGPT Export", command=self.load_file)
        self.load_button.pack(pady=10)
        
        # Date filter frame
        self.date_frame = tk.Frame(master)
        self.date_frame.pack(pady=5)

        self.from_date_label = tk.Label(self.date_frame, text="From Date (YYYY-MM-DD):")
        self.from_date_label.grid(row=0, column=0, padx=5)
        self.from_date_entry = tk.Entry(self.date_frame, width=15)
        self.from_date_entry.grid(row=0, column=1, padx=5)
        
        self.to_date_label = tk.Label(self.date_frame, text="To Date (YYYY-MM-DD):")
        self.to_date_label.grid(row=0, column=2, padx=5)
        self.to_date_entry = tk.Entry(self.date_frame, width=15)
        self.to_date_entry.grid(row=0, column=3, padx=5)
        
        # Fuzzy search options
        self.fuzzy_var = tk.BooleanVar()
        self.fuzzy_check = tk.Checkbutton(master, text="Enable Fuzzy Search", variable=self.fuzzy_var)
        self.fuzzy_check.pack(pady=5)
        
        self.threshold_frame = tk.Frame(master)
        self.threshold_frame.pack(pady=5)
        self.threshold_label = tk.Label(self.threshold_frame, text="Fuzzy Threshold (0-100):")
        self.threshold_label.grid(row=0, column=0, padx=5)
        self.threshold_entry = tk.Entry(self.threshold_frame, width=5)
        self.threshold_entry.grid(row=0, column=1, padx=5)
        self.threshold_entry.insert(0, "70")  # Default threshold
        
        # Search term label and entry
        self.search_label = tk.Label(master, text="Enter search term:")
        self.search_label.pack()
        
        self.search_entry = tk.Entry(master, width=50)
        self.search_entry.pack(pady=5)
        
        # Search button
        self.search_button = tk.Button(master, text="Search", command=self.search)
        self.search_button.pack(pady=10)
        
        # Scrolled text area to show search results
        self.results_text = scrolledtext.ScrolledText(master, width=80, height=20)
        self.results_text.pack(pady=10)
        
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Handle data structure: either a dict with a 'conversations' key or a list
                self.conversations = data.get("conversations", data)
                messagebox.showinfo("Success", f"Loaded {len(self.conversations)} conversations.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
                
    def search(self):
        term = self.search_entry.get().strip()
        if not term:
            messagebox.showwarning("Input needed", "Please enter a search term")
            return
        
        # Process date filters if provided
        from_date_str = self.from_date_entry.get().strip()
        to_date_str = self.to_date_entry.get().strip()
        from_date = None
        to_date = None
        date_format = "%Y-%m-%d"
        if from_date_str:
            try:
                from_date = datetime.strptime(from_date_str, date_format)
            except ValueError:
                messagebox.showerror("Error", "Invalid From Date format. Please use YYYY-MM-DD.")
                return
        if to_date_str:
            try:
                to_date = datetime.strptime(to_date_str, date_format)
            except ValueError:
                messagebox.showerror("Error", "Invalid To Date format. Please use YYYY-MM-DD.")
                return
        
        # Get fuzzy search option and threshold if enabled
        fuzzy_enabled = self.fuzzy_var.get()
        threshold = 70
        if fuzzy_enabled:
            try:
                threshold = int(self.threshold_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid threshold value. Using default 70.")
                threshold = 70
        
        self.results_text.delete("1.0", tk.END)
        results_found = False
        
        for conv in self.conversations:
            title = conv.get("title", "Untitled Conversation")
            messages = conv.get("messages", [])
            matching_messages = []
            for msg in messages:
                content = msg.get("content", "")
                
                # Date filtering: assume each message has a 'date' field in YYYY-MM-DD format
                msg_date_str = msg.get("date", None)
                msg_date = None
                if msg_date_str:
                    try:
                        msg_date = datetime.strptime(msg_date_str, date_format)
                    except ValueError:
                        pass  # If date parsing fails, skip date filtering for this message
                
                # Apply date filters if message has a valid date
                if msg_date:
                    if from_date and msg_date < from_date:
                        continue
                    if to_date and msg_date > to_date:
                        continue
                
                # Check for search term using fuzzy or exact matching
                if fuzzy_enabled:
                    # Use fuzzy matching ratio (case-insensitive)
                    match_ratio = fuzz.ratio(term.lower(), content.lower())
                    if match_ratio >= threshold:
                        matching_messages.append(f"(Fuzzy match {match_ratio}%) {content}")
                else:
                    if re.search(re.escape(term), content, re.IGNORECASE):
                        matching_messages.append(content)
                        
            if matching_messages:
                results_found = True
                self.results_text.insert(tk.END, f"Conversation: {title}\n")
                for msg in matching_messages:
                    self.results_text.insert(tk.END, f"    {msg}\n")
                self.results_text.insert(tk.END, "\n")
                
        if not results_found:
            self.results_text.insert(tk.END, "No matches found.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGPTSearchApp(root)
    root.mainloop()