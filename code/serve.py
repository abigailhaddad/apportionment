#!/usr/bin/env python3
"""
Simple HTTP server for serving the Education obligation summary website.
Serves static files with proper CORS headers for local development.
"""

import http.server
import socketserver
import os
from http.server import SimpleHTTPRequestHandler

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    # Try different ports if default is taken
    PORTS = [8000, 8001, 8080, 8888, 3000, 3001, 5000, 5001]
    
    # Change to the site directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    site_dir = os.path.join(script_dir, 'site')
    os.chdir(site_dir)
    
    httpd = None
    PORT = None
    
    # Try each port until we find an available one
    for port in PORTS:
        try:
            httpd = socketserver.TCPServer(("", port), CORSRequestHandler)
            PORT = port
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                continue
            else:
                raise
    
    if httpd is None:
        print("Error: Could not find an available port. Tried:", PORTS)
        return
    
    print(f"Server running at http://localhost:{PORT}/")
    print(f"View the dashboard at: http://localhost:{PORT}/index.html")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()