import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import re
import os
from datetime import datetime
from rapidfuzz import fuzz  # pip install rapidfuzz
from email.parser import BytesParser
from email.policy import default
from bs4 import BeautifulSoup  # pip install beautifulsoup4

class ChatGPTSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("ChatGPT Conversation Search")

        # Store all conversations from multiple loads (JSON or MHTML)
        self.conversations = []

        # --- LOAD FILES BUTTON ---
        self.load_button = tk.Button(
            master, text="Load ChatGPT Exports (JSON/MHTML)", command=self.load_files
        )
        self.load_button.pack(pady=10)

        # --- DATE FILTER FRAME ---
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

        # --- SEARCH OPTIONS FRAME ---
        self.options_frame = tk.Frame(master)
        self.options_frame.pack(pady=5)

        # Fuzzy search
        self.fuzzy_var = tk.BooleanVar()
        self.fuzzy_check = tk.Checkbutton(
            self.options_frame, text="Enable Fuzzy Search", variable=self.fuzzy_var
        )
        self.fuzzy_check.grid(row=0, column=0, padx=5, sticky="w")

        # Boolean operators
        self.boolean_var = tk.BooleanVar()
        self.boolean_check = tk.Checkbutton(
            self.options_frame, text="Use Boolean Operators", variable=self.boolean_var
        )
        self.boolean_check.grid(row=0, column=1, padx=5, sticky="w")

        # Regex mode
        self.regex_var = tk.BooleanVar()
        self.regex_check = tk.Checkbutton(
            self.options_frame, text="Regex Mode", variable=self.regex_var
        )
        self.regex_check.grid(row=0, column=2, padx=5, sticky="w")

        # --- FUZZY THRESHOLD ---
        self.threshold_frame = tk.Frame(master)
        self.threshold_frame.pack(pady=5)
        self.threshold_label = tk.Label(self.threshold_frame, text="Fuzzy Threshold (0-100):")
        self.threshold_label.grid(row=0, column=0, padx=5)
        self.threshold_entry = tk.Entry(self.threshold_frame, width=5)
        self.threshold_entry.grid(row=0, column=1, padx=5)
        self.threshold_entry.insert(0, "70")  # Default threshold

        # --- SEARCH TERM ---
        self.search_label = tk.Label(master, text="Enter search term (OR comma-separated):")
        self.search_label.pack()
        self.search_entry = tk.Entry(master, width=50)
        self.search_entry.pack(pady=5)

        # --- BUTTONS FRAME (SEARCH / CLEAR) ---
        self.buttons_frame = tk.Frame(master)
        self.buttons_frame.pack(pady=5)

        self.search_button = tk.Button(self.buttons_frame, text="Search", command=self.search)
        self.search_button.grid(row=0, column=0, padx=10)

        self.clear_button = tk.Button(self.buttons_frame, text="Clear Results", command=self.clear_results)
        self.clear_button.grid(row=0, column=1, padx=10)

        # --- RESULTS ---
        self.results_text = scrolledtext.ScrolledText(master, width=80, height=20)
        self.results_text.pack(pady=10)

    def load_files(self):
        """
        Load multiple JSON or MHTML files.
        - If .json, parse as JSON
        - If .mhtml, parse via naive MHTML -> HTML -> text approach
        """
        file_paths = filedialog.askopenfilenames(
            filetypes=[("JSON or MHTML Files", "*.json *.mhtml *.mht")]
        )
        if not file_paths:
            return  # user canceled

        total_loaded = 0
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            try:
                if ext == ".json":
                    new_convs = self.parse_json_file(file_path)
                    total_loaded += len(new_convs)
                    self.conversations.extend(new_convs)
                elif ext in [".mhtml", ".mht"]:
                    new_convs = self.parse_mhtml_file(file_path)
                    total_loaded += len(new_convs)
                    self.conversations.extend(new_convs)
                else:
                    messagebox.showwarning("Unsupported File", f"Skipping unsupported file type: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}:\n{e}")

        messagebox.showinfo("Success", f"Loaded {total_loaded} conversations in total.")

    def parse_json_file(self, file_path):
        """
        Parse a JSON file. The data may be:
          - A dict with a 'conversations' key
          - A list of conversation objects
        Return a list of conversation dicts.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and "conversations" in data:
            conv_data = data["conversations"]
        else:
            # Could be either a list of convs or a single conv
            conv_data = data
        
        if isinstance(conv_data, list):
            return conv_data
        elif isinstance(conv_data, dict):
            return [conv_data]
        else:
            return []

    def parse_mhtml_file(self, file_path):
        """
        Naive MHTML parsing:
        1) Read the .mhtml file as email message
        2) Extract the text/html part
        3) Parse with BeautifulSoup
        4) Gather text from <p> tags into a 'conversation' structure
        Return a list with a single conversation dict 
        (or more if you attempt advanced splits).
        """
        with open(file_path, 'rb') as f:
            msg = BytesParser(policy=default).parse(f)

        # We'll store everything in a single "conversation"
        conversation = {
            "title": f"MHTML conversation: {os.path.basename(file_path)}",
            "messages": []
        }

        # Walk through email parts and find text/html content
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_data = part.get_payload(decode=True)
                soup = BeautifulSoup(html_data, "html.parser")

                # Grab all <p> tags for demonstration.
                # For more accurate ChatGPT exports, you might need to find specific
                # classes, <div> sections, etc.
                paragraphs = soup.find_all("p")
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        # Just treat each paragraph as one "message"
                        conversation["messages"].append({
                            "content": text,
                            "date": None  # no date info in naive approach
                        })

        return [conversation]

    def clear_results(self):
        """Clear the results text area."""
        self.results_text.delete("1.0", tk.END)

    def search(self):
        """Perform the search across all loaded conversations."""
        term = self.search_entry.get().strip()
        if not term:
            messagebox.showwarning("Input needed", "Please enter a search term.")
            return

        # Process date filters if provided
        from_date_str = self.from_date_entry.get().strip()
        to_date_str = self.to_date_entry.get().strip()
        from_date = None
        to_date = None
        date_format = "%Y-%m-%d"

        # Validate date inputs
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

        # Fuzzy search option and threshold
        fuzzy_enabled = self.fuzzy_var.get()
        threshold = 70
        if fuzzy_enabled:
            try:
                threshold = int(self.threshold_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid threshold value. Using default 70.")
                threshold = 70

        # Boolean, regex modes
        boolean_enabled = self.boolean_var.get()
        regex_enabled = self.regex_var.get()

        self.results_text.delete("1.0", tk.END)
        results_found = False

        def content_matches(content, user_input):
            """Check if the content matches user_input, considering fuzzy/regex/boolean."""
            text_lower = content.lower()
            term_lower = user_input.lower()

            # Regex mode: ignore fuzzy/boolean
            if regex_enabled:
                try:
                    pattern = re.compile(user_input, re.IGNORECASE)
                    return bool(pattern.search(content))
                except re.error:
                    # If the user typed an invalid regex, treat as no match
                    return False

            # Boolean logic (naive single-operator approach)
            if boolean_enabled:
                if " AND " in user_input.upper():
                    parts = [p.strip() for p in user_input.upper().split("AND")]
                    if len(parts) == 2:
                        left, right = parts
                        return check_match(left, text_lower) and check_match(right, text_lower)
                    return False
                elif " OR " in user_input.upper():
                    parts = [p.strip() for p in user_input.upper().split("OR")]
                    if len(parts) == 2:
                        left, right = parts
                        return check_match(left, text_lower) or check_match(right, text_lower)
                    return False
                elif " NOT " in user_input.upper():
                    parts = [p.strip() for p in user_input.upper().split("NOT")]
                    if len(parts) == 2:
                        left, right = parts
                        return check_match(left, text_lower) and not check_match(right, text_lower)
                    return False
                else:
                    # No operator found, treat as single-term
                    return check_match(term_lower, text_lower)
            else:
                # If multiple terms separated by commas, we do an AND approach
                if "," in user_input:
                    splitted = [t.strip() for t in user_input.split(",") if t.strip()]
                    for part in splitted:
                        if not check_match(part.lower(), text_lower):
                            return False
                    return True
                else:
                    # single term
                    return check_match(term_lower, text_lower)

        def check_match(term_lower, text_lower):
            """Check a single term using fuzzy or exact match."""
            if fuzzy_enabled:
                match_ratio = fuzz.ratio(term_lower, text_lower)
                return match_ratio >= threshold
            else:
                # exact substring match, ignoring case
                return bool(re.search(re.escape(term_lower), text_lower, re.IGNORECASE))

        # Main loop over each conversation
        for idx, conv in enumerate(self.conversations):
            if not isinstance(conv, dict):
                self.results_text.insert(tk.END, f"Skipping item at index {idx}: not a dict.\n\n")
                continue

            title = conv.get("title", "Untitled Conversation")
            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                self.results_text.insert(tk.END, f"Skipping conversation '{title}' at index {idx}: messages not a list.\n\n")
                continue

            matching_messages = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                content = msg.get("content", "")
                msg_date_str = msg.get("date", None)
                msg_date = None
                if msg_date_str:
                    try:
                        msg_date = datetime.strptime(msg_date_str, date_format)
                    except ValueError:
                        pass  # ignoring invalid date

                # Apply date filters
                if msg_date:
                    if from_date and msg_date < from_date:
                        continue
                    if to_date and msg_date > to_date:
                        continue

                # Check if content matches
                if content_matches(content, term):
                    matching_messages.append(content)

            if matching_messages:
                results_found = True
                self.results_text.insert(tk.END, f"Conversation: {title}\n")
                for m in matching_messages:
                    self.results_text.insert(tk.END, f"    {m}\n")
                self.results_text.insert(tk.END, "\n")

        if not results_found:
            self.results_text.insert(tk.END, "No matches found.\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGPTSearchApp(root)
    root.mainloop()