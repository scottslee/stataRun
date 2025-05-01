import re
import sys
import os
from pathlib import Path

def evaluate_line(line, starting_unclosed_block_comment_count):

    unclosed_block_comment_count = starting_unclosed_block_comment_count # inherit from previous line

    # Skip completely empty lines
    if not line.strip():
        return (None, starting_unclosed_block_comment_count, False)

    # Separate line into leading whitespace and line stripped
    leading_whitespace = line[:len(line) - len(line.lstrip())]
    line_stripped = line.strip()
    
    # --- Comment Handling ---
    # For comment-checking, ignore all text that occurs after the first instance of '//' since this is ignored by Stata
    # This implcitly includes '///' as well, but we will handle it differently below
    has_triple_slash = False
    line_stripped_until_comment = line_stripped  # Initialize with full line by default

    if '//' in line_stripped:
        #print(f'* line_stripped: {line_stripped}')
        if line_stripped.startswith('//'):
            # Line begins with '//', so it's a comment and we skip
            return (None, starting_unclosed_block_comment_count, False)
        # Find position of first '//'
        comment_start = line_stripped.find('//')
        # Check if there's a third slash after the '//'
        if comment_start + 2 < len(line_stripped) and line_stripped[comment_start + 2] == '/':
            has_triple_slash = True
            # Keep everything up to and including the '///'
            line_stripped_until_comment = line_stripped[:comment_start + 3]
        else:
            # Keep everything up to and including the '//'
            line_stripped_until_comment = line_stripped[:comment_start + 2]
            
    #print(f'* line_stripped_until_comment: {line_stripped_until_comment}')

    # Search along the line, starting from the beginning and tally each /* and */ as we find them
    # We also classify each position as either part of comment (unclosed_block_comment_count > 0) or not (unclosed_block_comment_count == 0)    
    pos = 0
    is_comment = [False] * len(line_stripped_until_comment)
    
    while pos < len(line_stripped_until_comment): # Scan up to last position
        #print(f'* Unclosed block comment count: {unclosed_block_comment_count}')
        # Check for block comment markers if we have at least 2 characters remaining
        if pos + 1 < len(line_stripped_until_comment): # Scan up to second-to-last position
            # Extract the current first two characters
            current_chars = line_stripped_until_comment[pos:pos+2]
            
            if current_chars == '/*':
                unclosed_block_comment_count += 1
                is_comment[pos:pos+2] = [True, True]
                pos += 2
                continue
                
            if current_chars == '*/':
                unclosed_block_comment_count -= 1 if unclosed_block_comment_count > 0 else 0
                is_comment[pos:pos+2] = [True, True] # count marker as comment
                pos += 2
                continue
        
        # If we're inside a block comment, mark this character as commented
        if unclosed_block_comment_count > 0:
            is_comment[pos] = True
        else:
            is_comment[pos] = False
            
        pos += 1

    # Keep only the non-commented parts of the line
    remaining_line = ''.join([c for c, is_commented in zip(line_stripped_until_comment, is_comment) if not is_commented])
    remaining_line = remaining_line.strip()
    #print(f'* remaining_line: {remaining_line}')

    # If nothing remains, whole line is comment and we exit
    if not remaining_line:
        return (None, unclosed_block_comment_count, False)
    else:
        # Also exit if line comment
        if remaining_line.startswith(('*', '//')):
            return (None, unclosed_block_comment_count, False)    
    # --- End Comment Handling ---
    
    # --- Remainder is non-comment conent only ---

    # If line isn't a comment and has a non-commented '///' (not after a separate //), it's a multi-line command that we need to keep together with the next line
    # So we pass it to the next line and handle once we've reached the end of the command
    # Line ending in /// means first character of line after // is /, so we have to look at the other part of line_stripped
    if has_triple_slash:
        #print(f'* Previously had triple slash')
        # Check remaining_line to see if triple slash is still present (i.e., wasn't part of a comment)
        if remaining_line.find('///') != -1:
            #print(f'* Triple slash still present, continue to next line but remove triple slash first')
            # Triple slash is still present, so we need to keep this line and the next one together
            line_to_continue = leading_whitespace + remaining_line.replace('///', '')
            return (line_to_continue, unclosed_block_comment_count, True) # need to return leading_whitespace to add it after further stripping
        else:
            #print(f'* Triple slash no longer present, treating as normal line')
            pass

    # If original line is a first-level command, don't re-display it since Stata will display it
    # Note: This won't capture first-level commands that have been indented for aesthetic reasons, and it will also exclude any
    # second-level commands that *aren't* indented, but this shouldn't happen in practice
    if not line.startswith(' '):
        return (remaining_line, unclosed_block_comment_count, False)
    
    # For 'display' commands, we don't have to display the line, since Stata will show the quoted string as output
    # However, when processing 'display' command, Stata doesn't respect leading whitespace before the word 'display', so the outputted string
    # ends up being flush left. So we want to add the leading whitespace to the string in quotes as well as keep it in the line itself
    first_word = remaining_line.split()[0]
    if first_word in ['di', 'dis', 'disp', 'displ', 'displa', 'display']:
        # Find position of first quote
        quote_pos = remaining_line.find('"')
        if quote_pos != -1:
            # Found a quote, so preserve all text up to and including the first quote it, then interpolate leading whitespace after it
            pos_after_quote = quote_pos + 1
            string_up_to_quote = remaining_line[:pos_after_quote]
            string_after_quote = remaining_line[pos_after_quote:]
            show_line = f"{leading_whitespace}{string_up_to_quote}{leading_whitespace}{string_after_quote}"
    else:
        # For all other lines, combine leading whitspace and remaining line
        show_line = f"disp as error `\"{leading_whitespace}{remaining_line}\"'\n{leading_whitespace}{remaining_line}" # use `" and "' around disp string to avoid errors

    return (show_line, unclosed_block_comment_count, False)

def preprocess_stata_code(input_code):
    output_lines = []
    previous_line = ""
    unclosed_block_comment_count = 0
    continue_from_previous_line = False

    lines = input_code.splitlines()
    
    for line in lines:
        #output_lines.append(f"* NEW LINE: {line}")
        
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
                continue
            except FileNotFoundError:
                # Handle file not found error
                error_message = f"* ERROR: Could not open file: {do_file_path}"
                output_lines.append(error_message)
        else:
            # Prepend previous line to current line
            if previous_line:
                line = previous_line + ("" if previous_line.endswith(" ") else " ") + line.strip()

            new_line, unclosed_block_comment_count, continue_from_previous_line = evaluate_line(line, unclosed_block_comment_count)

            #print(f'* new_line: {new_line}')

            if continue_from_previous_line:
                # Move leading whitespace from new_line to beginning of previous_line
                leading_whitespace = new_line[:len(new_line) - len(new_line.lstrip())]
                # Add new_line (i-1) to current line (i) and don't output anything
                previous_line = leading_whitespace + previous_line + ("" if previous_line.endswith(" ") else " ") + new_line
                #output_lines.append(f"* Line continued to next line: <{previous_line}>")
                continue
            else:
                previous_line = "" # reset previous line since this is a new line
                if new_line is not None:
                    output_lines.append(new_line)
                else:
                    continue

    return "\n".join(output_lines)



# --- Main block to allow script execution --- 
if __name__ == "__main__":
    # Read from stdin, write to stdout
    input_code = sys.stdin.read()
    processed_code = preprocess_stata_code(input_code)
    print(processed_code)