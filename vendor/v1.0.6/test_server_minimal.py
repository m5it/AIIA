#!/usr/bin/env python3
"""Minimal test of server file API."""

import sys
sys.path.insert(0, '/home/t3ch/adata2/OurAI')

from server_profiles.HTTP import OurAIServer

# Mock Options
Options = {
    'working_dir': '/home/t3ch/adata2/OurAI/playground/collecting_program_data/t21',
    'SERVER_AUTH_ENABLED': False,
    'SERVER_USERNAME': 'admin',
    'SERVER_PASSWORD': 'aiia',
    'AI_QUICK': True,
}

print("Creating OurAIServer...")
server = OurAIServer('127.0.0.1', 5552, Options)
print(f"project_root = {server.project_root}")

print("\nTesting list_files...")
result = server.list_files("", recursive=False, root="/home/t3ch/adata2/OurAI/playground/collecting_program_data/t21")
print(f"Result: {result}")

print("\nTesting with no root override...")
result2 = server.list_files("", recursive=False)
print(f"Result: {result2}")
