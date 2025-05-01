import re
import sys
import os
from pathlib import Path

def evaluate_line(line):
    # If line is empty, just return it as is
    if not line.strip():
        return line

    # If line is a first-level command, don't display it again since Stata will display it
    if not line.startswith(' '):
        return line

    # Similarly, for 'display' commands, we don't have to display the command itself, since Stata will show the quoted string as output
    # However, when processing 'display' command, Stata doesn't respect the leading whitespace before the word 'display', so the string
    # ends up being flush left. So want to add the leading whitespace to the string in quotes as well as keep it in the line itself
    # (this issue is independent of this pre-processing script)
    leading_whitespace = line[:len(line) - len(line.lstrip())]
    line_stripped = line.strip() # Need original stripped for checks later and to return
    
    # Check if line_stripped is empty or has no words
    if not line_stripped or len(line_stripped.split()) == 0:
        return line
    
    first_word = line_stripped.split()[0]

    if first_word in ['di', 'disp', 'display']:
        # Find position of first quote
        quote_pos = line_stripped.find('"')
        if quote_pos != -1:
            # Found a quote, so preserve all text up to and including the first quote it, then interpolate leading whitespace after it
            pos_after_quote = quote_pos + 1
            string_up_to_quote = line_stripped[:pos_after_quote]
            string_after_quote = line_stripped[pos_after_quote:]
            show_line = f"{leading_whitespace}{string_up_to_quote}{leading_whitespace}{string_after_quote}"
        else:
            # No quotes found, handle as regular line
            show_line = f"disp as input `\"{line}\"'\n{line}"
    else:
        # For all other lines, {line} already includes whitespace before the command, so display it as is
        show_line = f"disp as input `\"{line}\"'\n{line}" # use `" and "' around disp string to avoid errors
    return show_line

def preprocess_stata_code(input_code):
    output_lines = []
    lines = input_code.splitlines()
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('run '):
            # If do-file calls/sources another do-file, we have to process it as well
            # So we need to load the do-file into memory and then run the 'for line in lines' loop on it
            do_file_path = line_stripped[4:].strip()
            # Expand ~ to home directory
            do_file_path = os.path.expanduser(do_file_path)
            # Convert to absolute path
            do_file_path = os.path.abspath(do_file_path)
            try:
                with open(do_file_path, 'r') as f:
                    do_file_code = f.read()
                processed_do_file_code = preprocess_stata_code(do_file_code)
                output_lines.append(processed_do_file_code)
            except FileNotFoundError:
                # Handle file not found error
                error_message = f"* ERROR: Could not open file: {do_file_path}"
                output_lines.append(error_message)
        else:
            new_line = evaluate_line(line)
            output_lines.append(new_line)
            
    return "\n".join(output_lines)

# --- Main block to allow script execution --- 
if __name__ == "__main__":
    # Read from stdin, write to stdout
    input_code = sys.stdin.read()
    processed_code = preprocess_stata_code(input_code)
    print(processed_code)