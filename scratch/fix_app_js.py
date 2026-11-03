import sys

def fix():
    with open('public/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # Locate where renderHallOfFame begins
    target_pattern = '  renderHallOfFame() {'
    idx = content.find(target_pattern)
    if idx == -1:
        print("ERROR: target pattern not found")
        sys.exit(1)

    prefix = content[:idx]
    suffix = content[idx:]

    # Remove the premature class closure and DOMContentLoaded listener right before renderHallOfFame
    class_close_str = "}\n\nwindow.addEventListener(\"DOMContentLoaded\", () => {\n  new F1App();\n});\n\n"
    class_close_crlf = "}\r\n\r\nwindow.addEventListener(\"DOMContentLoaded\", () => {\r\n  new F1App();\r\n});\r\n\r\n"

    if class_close_crlf in prefix:
        prefix = prefix.replace(class_close_crlf, "")
        print("Replaced CRLF class close")
    elif class_close_str in prefix:
        prefix = prefix.replace(class_close_str, "")
        print("Replaced LF class close")
    else:
        print("ERROR: class close not found in prefix")
        print("Last 150 chars of prefix:")
        print(repr(prefix[-150:]))
        sys.exit(1)

    new_content = prefix + suffix.rstrip() + "\n}\n\nwindow.addEventListener(\"DOMContentLoaded\", () => {\n  new F1App();\n});\n"
    
    with open('public/app.js', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_content)
    print("Successfully rewritten public/app.js")

if __name__ == '__main__':
    fix()

