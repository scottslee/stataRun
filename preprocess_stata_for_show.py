import re
import sys
import os
from pathlib import Path

# --- Configuration ---
# Skip block commands, 'preserve/restore' (for some reason 'preserve' doesn't register), and 'display' (will always show statement in output)
FORBIDDEN_TO_PREFIX = {'if', 'else', 'foreach', 'forvalues', 'while', 'program', 'end', 'preserve', 'restore', 'disp', 'di', 'display'}
# Look for the safelist in the same directory as this script
SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWED_COMMAND_FILE = os.path.join(SCRIPT_DIR, "show_commands_safe_list.csv")

# --- Load Safe First Word List ---
def load_allowed_commands(ALLOWED_COMMAND_FILE):
    # Check that file exists
    if not os.path.exists(ALLOWED_COMMAND_FILE):
        print(f"Error: File {ALLOWED_COMMAND_FILE} does not exist.")
        return set()

    with open(ALLOWED_COMMAND_FILE, 'r') as file:
        allowed_commands = file.read().splitlines()
    return set(allowed_commands)

ALLOWED_TO_PREFIX = load_allowed_commands(ALLOWED_COMMAND_FILE)
# Manually add qui/quietly as allowed *triggers* for the special handling
ALLOWED_TO_PREFIX.add('qui')
ALLOWED_TO_PREFIX.add('quietly')

def evaluate_line(line, ALLOWED_TO_PREFIX, in_block_comment):
    """
    Parses line and evaluates whether it can be echoed by `show` without error,
    considering block comment state.
    Returns: (bool: is_prefixable, bool: next_in_block_comment_state, str: original_line_stripped)
    """
    original_line_stripped = line.strip() # Need original stripped for checks later and to return

    # --- Block Comment Handling ---
    if in_block_comment:
        # We are already inside a block comment, look for the end
        next_state = '*/' not in line # in_block_comment is True if no end comment found
        return (original_line_stripped, False, next_state) # Never prefixable inside a block comment
    elif '/*' in line:
         # We are not inside a block comment, look for the start
         start_comment_pos = line.find('/*')
         end_comment_pos = line.find('*/', start_comment_pos + 2)
         next_state = (end_comment_pos == -1) # True if '*/' is NOT found after '/*'
         return (original_line_stripped, False, next_state) # Never prefix lines containing block comment markers
    # --- End Block Comment Handling ---

    # --- Existing Checks (run only if not starting/ending/inside a block comment) ---
    # Use original_line_stripped for checks that need it

    # 1. Skip empty lines
    if not original_line_stripped:
        return (None, False, False) # Not prefixable, not in block comment

    # 2. Pass through lines with no leading whitespace, as these are first-level commands that automatically echoed
    if not line.startswith(' '):
        return (original_line_stripped, False, False) # Not prefixable, not in block comment

    # 3. Pass through basic comments (*, //) - block comments already handled
    if original_line_stripped.startswith(('*', '//')):
        return (original_line_stripped, False, False) # Not prefixable, not in block comment

    # 4. Pass through lines containing braces OR /// anywhere
    if '{' in line or '}' in line or '///' in line:
        return (original_line_stripped, False, False) # Not prefixable, not in block comment

    # --- Command Evaluation ---
    #new_line_stripped = original_line_stripped # Initialize new line to original line
    parts = original_line_stripped.split(None, 1)
    first_word = parts[0]
    rest_of_line = parts[1].strip() if len(parts) > 1 else ""
    command_to_check = first_word

    # 6. Check for 'qui'/'quietly' and already prefixed 'show'
    if first_word in ['qui', 'quie', 'quiet', 'quietly', 'show ']:
        if len(parts) > 1:
            # Get the actual command after 'qui'/'quietly'
            actual_command_parts = rest_of_line.split(None, 1)
            command_to_check = actual_command_parts[0]
            if first_word == 'show ':
                original_line_stripped = actual_command_parts[1].strip() # Remove 'show ' from original line if present
        else:
             return (original_line_stripped, False, False) # Line was just 'qui'/'quietly' or 'show'

    # 7. Check command against allowed and forbidden lists
    if command_to_check in FORBIDDEN_TO_PREFIX:
        return (original_line_stripped, False, False) # Forbidden

    if command_to_check not in ALLOWED_TO_PREFIX:
         return (original_line_stripped, False, False) # Not explicitly allowed

    # If we reach here, the command is allowed and not forbidden
    # Return True for prefixable, and the the new line if modified (i.e., removal of 'snow ')
    # Other formatting logic will be handled by the caller
    # The state remains False as no new block comment started
    return (original_line_stripped, True, False)


def preprocess_stata_code(input_code, ALLOWED_TO_PREFIX):
    output_lines = []
    show_program_definition = """
capture program drop show
program define show
    if `"`0'"' != "" {
        display in red `"Nested: `0'"'
        `0'
    }
end
"""
    output_lines.extend(show_program_definition.strip().split('\n'))
    output_lines.append("")

    lines = input_code.splitlines()
    in_block_comment = False # State variable managed here

    for line in lines:
        # Pass current state to evaluate_line and get new line with any modifications + whether it's prefixable + next state
        new_line_stripped, is_prefixable, in_block_comment = evaluate_line(line, ALLOWED_TO_PREFIX, in_block_comment)

        if new_line_stripped is None:
            continue # Skip to next line
        elif is_prefixable:
            # New line exists and is prefixable, prefix with "show"
            leading_whitespace = line[:len(line) - len(line.lstrip())]
            output_lines.append(f"{leading_whitespace}show {new_line_stripped}")
        else:
            # Line is not prefixable, pass through original line
            output_lines.append(line)

    return "\n".join(output_lines)

# --- Main block to allow script execution --- 
if __name__ == "__main__":
    # Read from stdin, write to stdout
    input_code = sys.stdin.read()
    # Load safe list
    ALLOWED_TO_PREFIX = load_allowed_commands(ALLOWED_COMMAND_FILE)
    processed_code = preprocess_stata_code(input_code, ALLOWED_TO_PREFIX)
    print(processed_code)