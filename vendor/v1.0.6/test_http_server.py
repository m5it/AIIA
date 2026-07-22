#!/usr/bin/env python3
"""Minimal HTTP server for testing file API."""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class TestHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		print(format % args)
	
	def do_GET(self):
		print(f"GET {self.path}")
		
		if self.path == '/health':
			self._send_json(200, {"status": "ok"})
			return
		
		if self.path.startswith('/api/files/list'):
			self._handle_list()
			return
		
		self.send_response(404)
		self.end_headers()
	
	def _send_json(self, status, data):
		self.send_response(status)
		self.send_header('Content-Type', 'application/json')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		self.wfile.write(json.dumps(data).encode())
	
	def _handle_list(self):
		try:
			parsed = urlparse(self.path)
			params = parse_qs(parsed.query)
			path = params.get('path', [''])[0]
			root = self.headers.get('X-Project-Path', '/home/t3ch/adata2/OurAI/playground/collecting_program_data/t21')
			
			print(f"Listing files: path='{path}', root='{root}'")
			
			target = os.path.join(root, path) if path else root
			target = os.path.abspath(target)
			
			if not os.path.exists(target):
				self._send_json(404, {"error": "Path not found"})
				return
			
			files = []
			for item in sorted(os.listdir(target)):
				if item.startswith('.'):
					continue
				full = os.path.join(target, item)
				rel = os.path.relpath(full, root)
				files.append({
					"path": rel,
					"name": item,
					"is_directory": os.path.isdir(full),
					"size": os.path.getsize(full) if os.path.isfile(full) else None
				})
			
			self._send_json(200, {"files": files, "project_root": root})
			
		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()
			self._send_json(500, {"error": str(e)})


if __name__ == '__main__':
	server = HTTPServer(('0.0.0.0', 5551), TestHandler)
	print("Test server on http://0.0.0.0:5551")
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		print("\nShutting down")
