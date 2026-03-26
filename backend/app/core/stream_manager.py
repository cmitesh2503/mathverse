# backend/app/core/stream_manager.py

active_streams = {}

def start_stream(session_id):
    active_streams[session_id] = False  # not cancelled

def cancel_stream(session_id):
    active_streams[session_id] = True

def is_cancelled(session_id):
    return active_streams.get(session_id, False)

def end_stream(session_id):
    active_streams.pop(session_id, None)