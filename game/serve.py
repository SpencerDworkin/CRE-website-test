#!/usr/bin/env python3
"""Serve the game on http://localhost:8000/game.html and open a browser.

The page is an ES module and fetches its data, so it has to come off a server -
opening game.html straight off disk will not work in any modern browser.
"""
import http.server, os, socketserver, threading, webbrowser

PORT = int(os.environ.get('PORT', '8000'))
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
    url = f'http://localhost:{PORT}/game.html'
    print('RAD Soldiers is running at', url)
    print('press ctrl-c to stop')
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
