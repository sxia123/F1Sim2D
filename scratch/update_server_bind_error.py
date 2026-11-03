with open("server.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    # Bind before loading/saving a career or starting the simulation thread.
    # A duplicate launch must leave the running game and its save untouched.
    httpd = F1HTTPServer((args.host, args.port), F1RequestHandler)"""

replacement = """    # Bind before loading/saving a career or starting the simulation thread.
    # A duplicate launch must leave the running game and its save untouched.
    try:
        httpd = F1HTTPServer((args.host, args.port), F1RequestHandler)
    except OSError as err:
        # WinError 10048 on Windows, errno 98 (EADDRINUSE) on Linux, errno 48 on macOS
        if getattr(err, "winerror", None) == 10048 or err.errno in (10048, 98, 48):
            print(f"\\n==================================================================")
            print(f"  [SERVER LAUNCH ERROR] Port {args.port} is already in use!")
            print(f"==================================================================")
            print(f"  • A server instance is already running at: http://{args.host}:{args.port}")
            print(f"  • To run on an alternative port:")
            print(f"      python server.py --port {args.port + 1}")
            print(f"  • To stop the existing background server process on Windows:")
            print(f"      Stop-Process -Id (Get-NetTCPConnection -LocalPort {args.port}).OwningProcess -Force")
            print(f"==================================================================\\n")
            sys.exit(1)
        raise"""

assert target in text, "Could not find target in server.py"
text = text.replace(target, replacement, 1)

with open("server.py", "w", encoding="utf-8") as f:
    f.write(text)

print("server.py updated with friendly port error handling!")

