import sys

def check_js_syntax(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        src = f.read()

    stack = []
    i = 0
    line = 1
    col = 1
    n = len(src)

    while i < n:
        c = src[i]
        
        # Track line/col
        if c == '\n':
            line += 1
            col = 1
            i += 1
            continue
        else:
            col += 1

        # Skip line comments
        if c == '/' and i + 1 < n and src[i+1] == '/':
            while i < n and src[i] != '\n':
                i += 1
            continue

        # Skip block comments
        if c == '/' and i + 1 < n and src[i+1] == '*':
            i += 2
            while i + 1 < n and not (src[i] == '*' and src[i+1] == '/'):
                if src[i] == '\n':
                    line += 1
                    col = 1
                i += 1
            i += 2
            continue

        # Skip single or double quoted strings
        if c in ('"', "'"):
            quote = c
            start_line, start_col = line, col
            i += 1
            while i < n and src[i] != quote:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == '\n':
                    line += 1
                    col = 1
                i += 1
            if i >= n:
                print(f"Unterminated string literal starting at line {start_line}:{start_col}")
                return False
            i += 1
            continue

        # Template literals (handling ${...})
        if c == '`':
            start_line, start_col = line, col
            i += 1
            while i < n and src[i] != '`':
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == '$' and i + 1 < n and src[i+1] == '{':
                    # Inner expression in template string
                    stack.append(('}', line, col, 'template-expr'))
                    i += 2
                    break
                if src[i] == '\n':
                    line += 1
                    col = 1
                i += 1
            else:
                if i < n and src[i] == '`':
                    i += 1
                    continue
                else:
                    print(f"Unterminated template literal starting at line {start_line}:{start_col}")
                    return False
            continue

        # Braces
        if c in '({[':
            stack.append((c, line, col, 'bracket'))
            i += 1
            continue

        if c in ')}]':
            if not stack:
                print(f"Unexpected closing delimiter '{c}' at line {line}:{col}")
                return False
            top_char, top_line, top_col, top_type = stack.pop()
            matches = {'(': ')', '{': '}', '[': ']'}
            if top_type == 'template-expr':
                if c != '}':
                    print(f"Mismatched closing '{c}' at line {line}:{col}, expected '}}' for template expr from line {top_line}:{top_col}")
                    return False
                # Now resume template string after '}'
                i += 1
                while i < n and src[i] != '`':
                    if src[i] == '\\':
                        i += 2
                        continue
                    if src[i] == '$' and i + 1 < n and src[i+1] == '{':
                        stack.append(('}', line, col, 'template-expr'))
                        i += 2
                        break
                    if src[i] == '\n':
                        line += 1
                        col = 1
                    i += 1
                else:
                    if i < n and src[i] == '`':
                        i += 1
                continue
            else:
                expected = matches.get(top_char)
                if c != expected:
                    print(f"Mismatched closing '{c}' at line {line}:{col}, expected '{expected}' opened at line {top_line}:{top_col}")
                    return False
            i += 1
            continue

        i += 1

    if stack:
        for item in stack:
            print(f"Unclosed delimiter {item[0]} from line {item[1]}:{item[2]}")
        return False

    print("SUCCESS: public/app.js is balanced and syntactically sound!")
    return True

if __name__ == '__main__':
    ok = check_js_syntax('public/app.js')
    sys.exit(0 if ok else 1)

