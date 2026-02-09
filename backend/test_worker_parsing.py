
import pytest
import re

def parse_line(line, state):
    """Simplified version of the parsing logic in worker.py for testing"""
    # 1. Parse Folder Progress
    folder_match = re.search(r'Folder\s+(\d+)/(\d+)', line)
    if folder_match:
        state['current_folder'] = int(folder_match.group(1))
        state['total_folders'] = int(folder_match.group(2))
        if state['total_folders'] > 0:
            state['progress'] = int(((state['current_folder'] - 1) / state['total_folders']) * 100)
            state['message'] = f"Syncing folder {state['current_folder']}/{state['total_folders']}"
    
    # 2. Parse Message Total
    msg_total_match = re.search(r'has\s+(\d+)\s+messages\s+in\s+total', line)
    if msg_total_match:
        state['total_msgs'] = int(msg_total_match.group(1))

    # 3. Parse Message Progress
    msg_match = re.search(r'msg\s+.*?/(\d+)', line)
    if msg_match and state['total_folders'] > 0 and state['total_msgs'] > 0:
        current_msg = int(msg_match.group(1))
        base_p = ((state['current_folder'] - 1) / state['total_folders'])
        msg_p = (current_msg / state['total_msgs']) / state['total_folders']
        state['progress'] = int((base_p + msg_p) * 100)
        state['message'] = f"Folder {state['current_folder']}/{state['total_folders']}: msg {current_msg}/{state['total_msgs']}"

def test_imapsync_parsing_logic():
    state = {
        'current_folder': 0,
        'total_folders': 0,
        'total_msgs': 0,
        'progress': 0,
        'message': ''
    }
    
    # Init folders
    parse_line("Folder     1/10 [INBOX]                             -> [INBOX]", state)
    assert state['current_folder'] == 1
    assert state['total_folders'] == 10
    assert state['progress'] == 0
    
    # Message total
    parse_line("Host1: folder [INBOX] has 100 messages in total", state)
    assert state['total_msgs'] == 100
    
    # Message progress
    parse_line("msg INBOX/50 {1234} copied", state)
    # 5% (Folder 1 start at 0%, 50/100 messages in folder 1 = 50% of 1/10 = 5%)
    assert state['progress'] == 5
    assert "msg 50/100" in state['message']
    
    # Next folder
    parse_line("Folder     2/10 [Sent] -> [Sent]", state)
    assert state['current_folder'] == 2
    assert state['progress'] == 10 # 1/10 folders done
    
    # Message total for Sent
    parse_line("Host1: folder [Sent] has 200 messages in total", state)
    assert state['total_msgs'] == 200
    
    # Message in folder 2
    parse_line("msg Sent/100 {1234} copied", state)
    # 10% (Folder 1) + 100/200 messages in folder 2 (50% of 1/10 = 5%) = 15%
    assert state['progress'] == 15
