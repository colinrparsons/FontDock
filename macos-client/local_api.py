from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from config import LOCAL_API_PORT
from font_manager import FontManager


class AdobeBridgeHandler(BaseHTTPRequestHandler):
    font_manager = None
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'fontdock-client'}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/open-fonts':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                # Support both old format (font names) and new format (family/style pairs)
                font_list = data.get('fonts', [])
                
                results = []
                for font_item in font_list:
                    try:
                        # New format: {"family": "...", "style": "..."}
                        if isinstance(font_item, dict):
                            family = font_item.get('family')
                            style = font_item.get('style')
                            result = self.activate_font_by_family_style(family, style)
                        # Old format: "Font Name"
                        else:
                            result = self.activate_font_by_name(font_item)
                        results.append(result)
                    except Exception as e:
                        error_name = font_item if isinstance(font_item, str) else f"{font_item.get('family')} {font_item.get('style')}"
                        results.append({
                            'font_name': error_name,
                            'success': False,
                            'error': str(e)
                        })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def activate_font_by_family_style(self, family_name, style_name):
        """Activate font by exact family and style name match - most reliable method"""
        if not self.font_manager:
            raise RuntimeError("Font manager not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Searching by family/style: '{family_name}' / '{style_name}'")
        fonts = self.font_manager.db.search_font_by_family_and_style(family_name, style_name)
        logger.info(f"Family/style search returned {len(fonts)} results")
        
        if not fonts:
            raise ValueError(f"Font '{family_name} {style_name}' not found")
        
        if len(fonts) > 1:
            raise ValueError(f"Ambiguous font '{family_name} {style_name}' - {len(fonts)} matches found")
        
        font = fonts[0]
        logger.info(f"Activating font: {font['postscript_name']}")
        return self.font_manager.activate_font(font['id'])
    
    def activate_font_by_name(self, font_name):
        if not self.font_manager:
            raise RuntimeError("Font manager not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        # Try exact match first
        logger.info(f"Searching for font: '{font_name}'")
        fonts = self.font_manager.db.search_fonts(font_name)
        logger.info(f"Exact search returned {len(fonts)} results")
        
        # Helvetica Neue weight code mappings
        helvetica_weight_map = {
            '25 Ultra Light': 'UltLt',
            '35 Thin': 'Th',
            '45 Light': 'Lt',
            '46 Light Italic': 'LtIt',
            '55 Roman': 'Roman',
            '56 Italic': 'It',
            '65 Medium': 'Md',
            '66 Medium Italic': 'MdIt',
            '75 Bold': 'Bd',
            '76 Bold Italic': 'BdIt',
            '85 Heavy': 'Hv',
            '95 Black': 'Blk',
            '67 Medium Condensed': 'MdCn',
            '77 Bold Condensed': 'BdCn',
            '57 Condensed': 'Cn',
        }
        
        # If no exact match, try to match by converting to PostScript-style name
        # e.g., "Costa Display Wave Regular" -> "CostaDisplay-WaveRegular"
        if not fonts:
            # Split into family and style parts
            # Common patterns: "Family Style", "Family Multi Word Style"
            # Try different split points to find the right family/style boundary
            words = font_name.split()
            
            # Try splitting at different positions
            for split_pos in range(len(words) - 1, 0, -1):
                family_part = " ".join(words[:split_pos])
                style_part = " ".join(words[split_pos:])
                
                # Check if this is a Helvetica Neue font with weight code
                if "Helvetica Neue" in family_part and style_part in helvetica_weight_map:
                    # Use the abbreviated PostScript style name
                    ps_style = helvetica_weight_map[style_part]
                    ps_name = family_part.replace(" ", "") + "-" + ps_style
                    logger.info(f"Trying Helvetica weight mapping: '{ps_name}'")
                    fonts = self.font_manager.db.search_fonts(ps_name)
                    logger.info(f"Helvetica search returned {len(fonts)} results")
                    if fonts:
                        break
                
                # Convert to PostScript format: FamilyName-StyleName
                ps_name = family_part.replace(" ", "") + "-" + style_part.replace(" ", "")
                logger.info(f"Trying PostScript format: '{ps_name}'")
                fonts = self.font_manager.db.search_fonts(ps_name)
                logger.info(f"PostScript search returned {len(fonts)} results")
                
                if fonts:
                    break
        
        if not fonts:
            raise ValueError(f"Font '{font_name}' not found")
        
        if len(fonts) > 1:
            raise ValueError(f"Ambiguous font name '{font_name}' - {len(fonts)} matches found")
        
        font = fonts[0]
        logger.info(f"Activating font: {font['postscript_name']}")
        return self.font_manager.activate_font(font['id'])
    
    def log_message(self, format, *args):
        pass


class LocalAPIServer:
    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager
        self.server = None
        self.thread = None
    
    def start(self):
        AdobeBridgeHandler.font_manager = self.font_manager
        
        self.server = HTTPServer(('127.0.0.1', LOCAL_API_PORT), AdobeBridgeHandler)
        
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        print(f"Local API server started on http://127.0.0.1:{LOCAL_API_PORT}")
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
