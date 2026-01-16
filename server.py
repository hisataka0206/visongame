import http.server
import socketserver
import webbrowser
import os
import json
import glob

PORT = 8001  # Different port from photopop to avoid conflict

# Ensure we are serving the directory containing this script
web_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(web_dir)

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/icons':
            try:
                # List all png files in assets/icon
                icon_dir = os.path.join(web_dir, 'assets', 'icon')
                files = []
                if os.path.exists(icon_dir):
                    # Glob for .png files
                    pngs = glob.glob(os.path.join(icon_dir, '*.png'))
                    # Get just filenames
                    files = [os.path.basename(f) for f in pngs]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(files).encode('utf-8'))
            except Exception as e:
                print(f"Error listing icons: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            super().do_GET()

try:
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving Base Game at http://localhost:{PORT}")
        print("Please press Ctrl+C to stop the server.")
        
        url = f"http://localhost:{PORT}/index.html"
        print(f"Opening {url}...")
        webbrowser.open(url)
        
        httpd.serve_forever()
except OSError as e:
    print(f"Error: {e}")
    print(f"Port {PORT} might be in use. Try a different port.")
except KeyboardInterrupt:
    print("\nServer stopped.")
