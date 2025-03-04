import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import re
import os
import traceback
import tempfile
import platform
from datetime import datetime
from rapidfuzz import fuzz  # pip install rapidfuzz

class ChatGPTSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("ChatGPT Conversation Search")

        # Will store all conversations from any loaded JSON files
        self.conversations = []

        # A dictionary to map each "tag" in the text widget
        # to the conversation index that was clicked.
        self.tag_conversation_map = {}

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

        # Configure a "hyperlink" style tag for conversation titles
        # We'll bind <Button-1> to a callback so they become clickable.
        self.results_text.tag_configure("hyperlink", foreground="blue", underline=True)
        self.results_text.tag_bind("hyperlink", "<Button-1>", self.on_title_click)


    # =========================================================================
    # =  FILE LOADING (JSON only)
    # =========================================================================
    def load_files(self):
        """
        Load one or more JSON files. The top-level is either a list of 
        conversation objects or a single object. Each conversation object
        has a 'mapping' field with messages. 
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
        Parse the JSON file into a list of conversation dicts:
          { "title": <string>,
            "messages": [
               { "author": <str>,
                 "content": <str>,
                 "date": <datetime or None> },
               ...
            ]
          }
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # If the data is not a list, wrap it in one
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

                    author_data = msg.get("author", {})
                    author_role = author_data.get("role", "unknown")

                    content_info = msg.get("content", {})
                    parts = content_info.get("parts", [])
                    if not parts:
                        continue  # nothing to search

                    text_content = "\n".join(str(p) for p in parts if p)

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
        self.tag_conversation_map.clear()

    def search(self):
        """
        Supports exact, fuzzy, boolean, or regex searching of message content,
        plus optional date filtering if a message's date is available.
        """
        term = self.search_entry.get().strip()
        if not term:
            messagebox.showwarning("Input needed", "Please enter a search term.")
            return

        # DATE FILTERS
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

        # FUZZY SETTINGS
        fuzzy_enabled = self.fuzzy_var.get()
        threshold = 70
        if fuzzy_enabled:
            try:
                threshold = int(self.threshold_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid threshold value. Using default 70.")
                threshold = 70

        # BOOLEAN / REGEX
        boolean_enabled = self.boolean_var.get()
        regex_enabled = self.regex_var.get()

        self.results_text.delete("1.0", tk.END)
        self.tag_conversation_map.clear()

        results_found = False

        # local helper functions
        def content_matches(content, user_input):
            """
            Checks if 'content' matches 'user_input' under selected modes:
            - Regex => ignore fuzzy/boolean
            - Boolean => single operator (AND/OR/NOT)
            - Comma => multiple terms (AND logic)
            - Single term => exact or fuzzy
            """
            text_lower = content.lower()
            term_lower = user_input.lower()

            # 1) REGEX
            if regex_enabled:
                try:
                    pattern = re.compile(user_input, re.IGNORECASE)
                    return bool(pattern.search(content))
                except re.error:
                    return False

            # 2) BOOLEAN single-operator
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
                    return check_match(term_lower, text_lower)
            else:
                # 3) Comma => multiple terms (AND logic)
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
            """Exact vs fuzzy matching."""
            if fuzzy_enabled:
                match_ratio = fuzz.ratio(term_lower, text_lower)
                return match_ratio >= threshold
            else:
                return bool(re.search(re.escape(term_lower), text_lower, re.IGNORECASE))

        # MAIN SEARCH LOOP
        for idx, conv in enumerate(self.conversations):
            if not isinstance(conv, dict):
                continue

            title = conv.get("title", "Untitled Conversation")
            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                continue

            # We'll collect (date, content) for each matching message
            found_for_conversation = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                content = msg.get("content", "")
                msg_date = msg.get("date")  # datetime or None

                # Date filter if valid date
                if isinstance(msg_date, datetime):
                    if from_date and msg_date < from_date:
                        continue
                    if to_date and msg_date > to_date:
                        continue

                # Check content
                if content_matches(content, term):
                    found_for_conversation.append((msg_date, content))

            # If any messages matched in this conversation, display them
            if found_for_conversation:
                results_found = True

                # Insert "Conversation: <title>" with a hyperlink tag
                start_index = self.results_text.index("end")
                self.results_text.insert("end", "Conversation: ", ("normal",))
                
                # Insert the clickable title
                # We'll create a unique tag name for this conversation so we can map it.
                tag_name = f"conv_tag_{idx}"
                self.results_text.insert("end", title, (tag_name, "hyperlink"))
                self.results_text.insert("end", "\n")

                # Map the conversation index so the hyperlink knows which convo was clicked
                self.tag_conversation_map[tag_name] = idx

                # Show matching messages
                for (dt, msg_content) in found_for_conversation:
                    if dt is not None:
                        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = "NoDate"
                    self.results_text.insert("end", f"    [{date_str}] {msg_content}\n")

                self.results_text.insert("end", "\n")

        if not results_found:
            self.results_text.insert("end", "No matches found.\n")


    # =========================================================================
    # =  TITLE CLICK CALLBACK
    # =========================================================================
    def on_title_click(self, event):
        """
        Called when the user clicks on a conversation title in the results_text.
        We figure out which tag was clicked, look it up in self.tag_conversation_map,
        and open the relevant conversation in a new window.
        """
        # Get the index of the mouse click
        index = self.results_text.index(f"@{event.x},{event.y}")
        # Get all tags at that index (there could be multiple)
        tags = self.results_text.tag_names(index)
        # Find if any of them is one of our "conv_tag_X" names
        for t in tags:
            if t in self.tag_conversation_map:
                # We found the conversation index
                convo_index = self.tag_conversation_map[t]
                self.open_conversation_window(convo_index)
                break

    def open_conversation_window(self, convo_index):
        """
        Opens a new Toplevel window showing the entire conversation,
        plus a "Print" button.
        """
        if convo_index < 0 or convo_index >= len(self.conversations):
            return

        convo_data = self.conversations[convo_index]
        title = convo_data.get("title", "Untitled Conversation")
        messages = convo_data.get("messages", [])

        # Create a new window
        win = tk.Toplevel(self.master)
        win.title(f"Conversation: {title}")

        # Add a scrolled text to show the entire conversation
        text_area = scrolledtext.ScrolledText(win, width=80, height=20)
        text_area.pack(padx=10, pady=10)

        # Insert all messages
        text_area.insert("end", f"FULL CONVERSATION: {title}\n\n")
        for msg in messages:
            dt = msg.get("date")
            if isinstance(dt, datetime):
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = "NoDate"
            author = msg.get("author", "unknown")
            content = msg.get("content", "")
            text_area.insert("end", f"[{dt_str}] ({author})\n{content}\n\n")

        # Make text read-only
        text_area.config(state="disabled")

        # Add a Print button
        print_button = tk.Button(win, text="Print This Conversation",
                                 command=lambda: self.print_conversation(title, messages))
        print_button.pack(pady=5)


    # =========================================================================
    # =  PRINT LOGIC
    # =========================================================================
    def print_conversation(self, title, messages):
        """
        Create a temporary .txt file with the conversation, then attempt to print it.
        On Windows, we can do os.startfile(file, "print"). On other platforms,
        might need a different approach or simply show a "saved" message.
        """
        # Construct the text
        output_lines = []
        output_lines.append(f"TITLE: {title}")
        output_lines.append("")

        for msg in messages:
            dt = msg.get("date")
            author = msg.get("author", "unknown")
            content = msg.get("content", "")
            if isinstance(dt, datetime):
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = "NoDate"
            output_lines.append(f"[{dt_str}] ({author})")
            output_lines.append(content)
            output_lines.append("")

        full_text = "\n".join(output_lines)

        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
            tmp_file_path = tmp.name
            tmp.write(full_text)

        # Attempt to print
        current_os = platform.system().lower()

        if "windows" in current_os:
            try:
                os.startfile(tmp_file_path, "print")
            except Exception as e:
                messagebox.showerror("Print Error", f"Could not print on Windows:\n{e}")
        else:
            # For macOS/Linux, there's no direct cross-platform single command.
            # We can show a message or try 'lp' / 'lpr':
            # os.system(f"lp '{tmp_file_path}'")
            # or just let the user open the file manually.
            messagebox.showinfo("Print Info",
                f"Temporary file created:\n{tmp_file_path}\n"
                 "Open/print manually or adapt code for 'lpr' / 'lp' if on macOS/Linux.")


    # =========================================================================
    # =  Utility: Convert float timestamps to datetime
    # =========================================================================
    def convert_timestamp_to_date(self, ts):
        """
        Takes a numeric timestamp (float) like 1741047323.73435 and attempts to
        convert it to a datetime, if it's plausible as a Unix timestamp.
        Return None if invalid or if ts is null/0 or below some threshold.
        
        Replace utcfromtimestamp with fromtimestamp if you'd prefer local time.
        """
        if not ts:
            return None

        if ts > 1e9:  # simple heuristic
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