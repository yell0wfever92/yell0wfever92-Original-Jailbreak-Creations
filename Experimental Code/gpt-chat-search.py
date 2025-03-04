import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import re
import os
import traceback
from datetime import datetime
from rapidfuzz import fuzz  # pip install rapidfuzz

class ChatGPTSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("ChatGPT Conversation Search")

        # Will store all conversations from any loaded JSON files
        self.conversations = []

        # ---------------------------------------------------------------------
        # 1) LOAD FILES BUTTON
        # ---------------------------------------------------------------------
        self.load_button = tk.Button(
            master, text="Load JSON Exports", command=self.load_files
        )
        self.load_button.pack(pady=10)

        # ---------------------------------------------------------------------
        # 2) DATE FILTER FRAME
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # 3) SEARCH OPTIONS FRAME (FUZZY, BOOLEAN, REGEX)
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # 4) FUZZY THRESHOLD
        # ---------------------------------------------------------------------
        self.threshold_frame = tk.Frame(master)
        self.threshold_frame.pack(pady=5)
        self.threshold_label = tk.Label(self.threshold_frame, text="Fuzzy Threshold (0-100):")
        self.threshold_label.grid(row=0, column=0, padx=5)
        self.threshold_entry = tk.Entry(self.threshold_frame, width=5)
        self.threshold_entry.grid(row=0, column=1, padx=5)
        self.threshold_entry.insert(0, "70")  # Default threshold

        # ---------------------------------------------------------------------
        # 5) SEARCH TERM
        # ---------------------------------------------------------------------
        self.search_label = tk.Label(master, text="Enter search term (OR comma-separated):")
        self.search_label.pack()
        self.search_entry = tk.Entry(master, width=50)
        self.search_entry.pack(pady=5)

        # ---------------------------------------------------------------------
        # 6) BUTTONS FRAME (SEARCH / CLEAR)
        # ---------------------------------------------------------------------
        self.buttons_frame = tk.Frame(master)
        self.buttons_frame.pack(pady=5)

        self.search_button = tk.Button(self.buttons_frame, text="Search", command=self.search)
        self.search_button.grid(row=0, column=0, padx=10)

        self.clear_button = tk.Button(self.buttons_frame, text="Clear Results", command=self.clear_results)
        self.clear_button.grid(row=0, column=1, padx=10)

        # ---------------------------------------------------------------------
        # 7) RESULTS AREA
        # ---------------------------------------------------------------------
        self.results_text = scrolledtext.ScrolledText(master, width=80, height=20)
        self.results_text.pack(pady=10)


    # =========================================================================
    # =  FILE LOADING (JSON only)
    # =========================================================================
    def load_files(self):
        """
        Load one or more JSON files containing the schema:
          [
            {
              "title": "some title",
              "create_time": <float or null>,
              "update_time": <float or null>,
              "mapping": {
                "<some-id>": {
                  "message": {
                    "author": {"role": "user"/"assistant"/...},
                    "create_time": <float or null>,
                    "content": { "parts": [...] }
                  },
                  ...
                },
                ...
              }
            },
            ...
          ]
        """
        file_paths = filedialog.askopenfilenames(
            filetypes=[("JSON Files", "*.json")]
        )
        if not file_paths:
            return  # user canceled

        total_loaded = 0
        for file_path in file_paths:
            try:
                new_convs = self.parse_json_file(file_path)
                self.conversations.extend(new_convs)
                total_loaded += len(new_convs)
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Error", f"Failed to load {file_path}:\n{e}")

        messagebox.showinfo("Success", f"Loaded {total_loaded} conversations in total.")


    def parse_json_file(self, file_path):
        """
        Parses the file as JSON.
        The top-level structure is either a list of conversation objects or a single object.
        For each conversation object:
          - "title": "string"
          - "mapping": { ... }  # each entry has "message"
            - skip if message is null or if content.parts is empty
          - we store messages with possible date from create_time
        Returns a list of conversation dicts: { "title": ..., "messages": [...] }
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # The top-level might be a list of conversations or a single conversation
        if not isinstance(data, list):
            data = [data]

        all_conversations = []
        for conv_obj in data:
            title = conv_obj.get("title", "Untitled Conversation")
            mapping = conv_obj.get("mapping", {})
            messages = []

            if isinstance(mapping, dict):
                for _, map_entry in mapping.items():
                    msg = map_entry.get("message")
                    if not msg:
                        continue  # null or missing message

                    # get author
                    author_role = "unknown"
                    author_data = msg.get("author", {})
                    if "role" in author_data:
                        author_role = author_data["role"]

                    # get content parts
                    content_info = msg.get("content", {})
                    parts = content_info.get("parts", [])
                    if not parts:
                        continue  # empty text, skip

                    text_content = "\n".join(str(p) for p in parts if p)

                    # parse create_time as a date if it's a plausible timestamp
                    msg_date = self.convert_timestamp_to_date(msg.get("create_time"))

                    messages.append({
                        "author": author_role,
                        "content": text_content,
                        "date": msg_date
                    })

            conversation_dict = {
                "title": title,
                "messages": messages
            }
            all_conversations.append(conversation_dict)

        return all_conversations


    # =========================================================================
    # =  SEARCH LOGIC
    # =========================================================================
    def clear_results(self):
        self.results_text.delete("1.0", tk.END)

    def search(self):
        """
        Allows exact, fuzzy, boolean, or regex searching of message content,
        plus an optional date filter if a date is present.
        """
        term = self.search_entry.get().strip()
        if not term:
            messagebox.showwarning("Input needed", "Please enter a search term.")
            return

        # Date filters
        from_date_str = self.from_date_entry.get().strip()
        to_date_str = self.to_date_entry.get().strip()
        from_date = None
        to_date = None
        date_format = "%Y-%m-%d"

        if from_date_str:
            try:
                from_date = datetime.strptime(from_date_str, date_format)
            except ValueError:
                messagebox.showerror("Error", "Invalid From Date format. Use YYYY-MM-DD.")
                return

        if to_date_str:
            try:
                to_date = datetime.strptime(to_date_str, date_format)
            except ValueError:
                messagebox.showerror("Error", "Invalid To Date format. Use YYYY-MM-DD.")
                return

        # Fuzzy settings
        fuzzy_enabled = self.fuzzy_var.get()
        threshold = 70
        if fuzzy_enabled:
            try:
                threshold = int(self.threshold_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid threshold value. Using default 70.")
                threshold = 70

        # Boolean / regex modes
        boolean_enabled = self.boolean_var.get()
        regex_enabled = self.regex_var.get()

        self.results_text.delete("1.0", tk.END)
        results_found = False

        def content_matches(content, user_input):
            """
            Checks if 'content' matches 'user_input' under selected modes:
            - Regex => ignore fuzzy/boolean
            - Boolean => single operator (AND/OR/NOT)
            - Else => if comma present => multiple terms (AND logic),
                      else single-term exact or fuzzy.
            """
            text_lower = content.lower()
            term_lower = user_input.lower()

            # 1) Regex mode
            if regex_enabled:
                try:
                    pattern = re.compile(user_input, re.IGNORECASE)
                    return bool(pattern.search(content))
                except re.error:
                    return False

            # 2) Boolean single-operator
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
                    # No recognized operator => single term
                    return check_match(term_lower, text_lower)
            else:
                # 3) If commas => multiple terms (AND logic)
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
            """Helper for exact vs. fuzzy matching."""
            if fuzzy_enabled:
                match_ratio = fuzz.ratio(term_lower, text_lower)
                return match_ratio >= threshold
            else:
                return bool(re.search(re.escape(term_lower), text_lower, re.IGNORECASE))

        # Main search loop
        for idx, conv in enumerate(self.conversations):
            if not isinstance(conv, dict):
                self.results_text.insert(tk.END, f"Skipping item at index {idx}: not a dict.\n\n")
                continue

            title = conv.get("title", "Untitled Conversation")
            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                self.results_text.insert(
                    tk.END, f"Skipping conversation '{title}' at index {idx}: messages not a list.\n\n"
                )
                continue

            matching_messages = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                content = msg.get("content", "")
                msg_date = msg.get("date")

                # Date filter if we have a valid datetime
                if isinstance(msg_date, datetime):
                    if from_date and msg_date < from_date:
                        continue
                    if to_date and msg_date > to_date:
                        continue

                # Check content
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


    # =========================================================================
    # =  Utility: Convert float timestamps to datetime
    # =========================================================================
    def convert_timestamp_to_date(self, ts):
        """
        Takes a numeric timestamp (float) like 1741047323.73435 and attempts to
        convert it to a datetime, if it's plausible as a Unix timestamp.
        Return None if invalid or if ts is null/0 or below some threshold.
        """
        if not ts:
            return None

        # We'll assume anything > 1e9 is a plausible Unix timestamp in seconds
        if ts > 1e9:
            try:
                return datetime.utcfromtimestamp(ts)
            except (OverflowError, OSError, ValueError):
                pass
        return None


# -----------------------------------------------------------------------------
# Run the app
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGPTSearchApp(root)
    root.mainloop()