"""
HTTP server for receiving font requests from InDesign.
Runs on localhost:8765 and handles POST requests to /open-fonts
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
from threading import Thread

logger = logging.getLogger(__name__)


class FontRequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests from InDesign scripts."""
    
    # Class variable to store the callback function
    callback = None
    
    def do_POST(self):
        """Handle POST requests to /open-fonts"""
        if self.path == '/open-fonts':
            try:
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Parse JSON
                data = json.loads(post_data.decode('utf-8'))
                
                logger.info(f"Received font request from InDesign: {data.get('document_name')}")
                logger.debug(f"Missing fonts: {data.get('missing_fonts')}")
                
                # Call the callback function if set
                if self.callback:
                    self.callback(data)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'success', 'message': 'Request received'})
                self.wfile.write(response.encode('utf-8'))
                
            except Exception as e:
                logger.error(f"Error processing font request: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'error', 'message': str(e)})
                self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger instead of printing to stderr"""
        logger.debug(f"HTTP: {format % args}")


class FontDockHTTPServer:
    """HTTP server for receiving font requests from InDesign."""
    
    def __init__(self, port=8765, callback=None):
        self.port = port
        self.callback = callback
        self.server = None
        self.thread = None
        
    def start(self):
        """Start the HTTP server in a background thread."""
        try:
            # Set the callback on the handler class
            FontRequestHandler.callback = self.callback
            
            # Create server
            self.server = HTTPServer(('127.0.0.1', self.port), FontRequestHandler)
            
            # Start in background thread
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            logger.info(f"FontDock HTTP server started on http://127.0.0.1:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False
    
    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            logger.info("FontDock HTTP server stopped")
