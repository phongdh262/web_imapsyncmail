"""
test_worker_extended.py
Extended worker tests for imapsync log parsing, process management,
and progress calculation logic.
"""

import pytest
import re
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# ==========================================
# Parsing Helper (same as test_worker_parsing.py)
# ==========================================

def parse_line(line, state):
    """Simplified version of the parsing logic in worker.py for testing"""
    # 1. Parse Folder Progress
    folder_match = re.search(r'Folder\s+(\d+)/(\d+)', line)
    if folder_match:
        state['current_folder'] = int(folder_match.group(1))
        state['total_folders'] = int(folder_match.group(2))
        state['total_msgs'] = 0  # Reset for new folder
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

        # Dynamic total update (from worker.py)
        if current_msg > state['total_msgs']:
            state['total_msgs'] = current_msg

        base_p = ((state['current_folder'] - 1) / state['total_folders'])
        msg_p = (current_msg / state['total_msgs']) / state['total_folders']
        progress = int((base_p + msg_p) * 100)

        # Clamp to 100
        if progress > 100:
            progress = 100

        state['progress'] = progress
        state['message'] = f"Folder {state['current_folder']}/{state['total_folders']}: msg {current_msg}/{state['total_msgs']}"

    # 4. Parse Data Transfer
    if "Total bytes transferred" in line:
        match = re.search(r'Total bytes transferred.*?:\s*(\d+)', line, re.IGNORECASE)
        if match:
            state['bytes_transferred'] = int(match.group(1))


def new_state():
    """Create a fresh parsing state"""
    return {
        'current_folder': 0,
        'total_folders': 0,
        'total_msgs': 0,
        'progress': 0,
        'message': '',
        'bytes_transferred': 0
    }


# ==========================================
# 1. Folder Parsing Tests
# ==========================================

class TestFolderParsing:
    """Tests for imapsync folder progress parsing"""

    def test_parse_first_folder(self):
        """First folder sets progress to 0%"""
        state = new_state()
        parse_line("Folder     1/10 [INBOX]  -> [INBOX]", state)
        assert state['current_folder'] == 1
        assert state['total_folders'] == 10
        assert state['progress'] == 0  # (1-1)/10 = 0%

    def test_parse_middle_folder(self):
        """Middle folder (5/10) sets progress to 40%"""
        state = new_state()
        parse_line("Folder     5/10 [Drafts]  -> [Drafts]", state)
        assert state['current_folder'] == 5
        assert state['progress'] == 40  # (5-1)/10 = 40%

    def test_parse_last_folder(self):
        """Last folder (10/10) sets progress to 90%"""
        state = new_state()
        parse_line("Folder    10/10 [Archive]  -> [Archive]", state)
        assert state['current_folder'] == 10
        assert state['total_folders'] == 10
        assert state['progress'] == 90  # (10-1)/10 = 90%

    def test_parse_single_folder(self):
        """Job with only 1 folder"""
        state = new_state()
        parse_line("Folder     1/1 [INBOX]  -> [INBOX]", state)
        assert state['current_folder'] == 1
        assert state['total_folders'] == 1
        assert state['progress'] == 0  # (1-1)/1 = 0%

    def test_parse_two_folders(self):
        """Job with 2 folders"""
        state = new_state()
        parse_line("Folder     1/2 [INBOX]  -> [INBOX]", state)
        assert state['progress'] == 0  # (1-1)/2 = 0%

        parse_line("Folder     2/2 [Sent]  -> [Sent]", state)
        assert state['progress'] == 50  # (2-1)/2 = 50%

    def test_folder_resets_message_count(self):
        """New folder resets total_msgs"""
        state = new_state()
        parse_line("Folder     1/5 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 100 messages in total", state)
        assert state['total_msgs'] == 100

        parse_line("Folder     2/5 [Sent]  -> [Sent]", state)
        assert state['total_msgs'] == 0  # Reset for new folder


# ==========================================
# 2. Message Parsing Tests
# ==========================================

class TestMessageParsing:
    """Tests for message-level progress parsing"""

    def test_parse_message_progress(self):
        """Parse message progress within a folder"""
        state = new_state()
        parse_line("Folder     1/10 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 100 messages in total", state)
        parse_line("msg INBOX/50 {1234} copied", state)

        assert state['progress'] == 5  # (0 + 50/100/10) * 100 = 5%
        assert "msg 50/100" in state['message']

    def test_parse_complete_folder_messages(self):
        """All messages in a folder processed"""
        state = new_state()
        parse_line("Folder     1/4 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 50 messages in total", state)
        parse_line("msg INBOX/50 {1234} copied", state)

        assert state['progress'] == 25  # (0 + 50/50/4) * 100 = 25%

    def test_parse_zero_messages(self):
        """Folder with 0 messages (should not crash)"""
        state = new_state()
        parse_line("Folder     1/5 [Empty]  -> [Empty]", state)
        parse_line("Host1: folder [Empty] has 0 messages in total", state)

        # msg line should be ignored since total_msgs is 0
        parse_line("msg Empty/1 {100} copied", state)
        assert state['progress'] == 0  # No crash, no update

    def test_message_exceed_total_dynamic_update(self):
        """current_msg > total_msgs triggers dynamic update"""
        state = new_state()
        parse_line("Folder     1/2 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 10 messages in total", state)

        # Msg 15 exceeds stated total of 10
        parse_line("msg INBOX/15 {1234} copied", state)
        assert state['total_msgs'] == 15  # Dynamically updated
        assert state['progress'] <= 100


# ==========================================
# 3. Large Numbers Tests
# ==========================================

class TestLargeNumbers:
    """Tests with large folder/message counts"""

    def test_parse_many_folders(self):
        """1000 folders"""
        state = new_state()
        parse_line("Folder   500/1000 [Folder500]  -> [Folder500]", state)
        assert state['current_folder'] == 500
        assert state['total_folders'] == 1000
        # (500-1)/1000 = 49.9% -> 49
        assert state['progress'] == 49

    def test_parse_many_messages(self):
        """10000 messages in a folder"""
        state = new_state()
        parse_line("Folder     1/2 [Big]  -> [Big]", state)
        parse_line("Host1: folder [Big] has 10000 messages in total", state)
        parse_line("msg Big/5000 {4096} copied", state)

        # (0 + 5000/10000/2) * 100 = 25%
        assert state['progress'] == 25


# ==========================================
# 4. Progress Clamping Tests
# ==========================================

class TestProgressClamping:
    """Tests to ensure progress never exceeds 100%"""

    def test_progress_clamp_at_100(self):
        """Progress should never exceed 100%"""
        state = new_state()
        parse_line("Folder     1/1 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 10 messages in total", state)
        # Simulate a message count exceeding total
        parse_line("msg INBOX/20 {1234} copied", state)

        assert state['progress'] <= 100

    def test_progress_at_99_percent(self):
        """Near-complete progress"""
        state = new_state()
        parse_line("Folder    10/10 [Last]  -> [Last]", state)
        parse_line("Host1: folder [Last] has 100 messages in total", state)
        parse_line("msg Last/99 {1234} copied", state)

        # (9/10 + 99/100/10) * 100 = (0.9 + 0.099) * 100 = 99.9 -> 99
        assert state['progress'] == 99


# ==========================================
# 5. Data Transfer Parsing Tests
# ==========================================

class TestDataTransferParsing:
    """Tests for data transfer byte parsing"""

    def test_parse_bytes_transferred(self):
        """Parse Total bytes transferred line"""
        state = new_state()
        parse_line("Total bytes transferred : 1234567890", state)
        assert state['bytes_transferred'] == 1234567890

    def test_parse_bytes_zero(self):
        """Parse zero bytes transferred"""
        state = new_state()
        parse_line("Total bytes transferred : 0", state)
        assert state['bytes_transferred'] == 0

    def test_parse_bytes_large(self):
        """Parse very large byte count (10GB)"""
        state = new_state()
        big_bytes = 10 * (1024 ** 3)
        parse_line(f"Total bytes transferred : {big_bytes}", state)
        assert state['bytes_transferred'] == big_bytes


# ==========================================
# 6. Status Line Parsing Tests
# ==========================================

class TestStatusLineParsing:
    """Tests for general status line handling"""

    def test_no_crash_on_empty_line(self):
        """Empty line doesn't crash parser"""
        state = new_state()
        parse_line("", state)
        assert state['progress'] == 0

    def test_no_crash_on_random_text(self):
        """Random text doesn't crash parser"""
        state = new_state()
        parse_line("This is a random log line with no useful info", state)
        assert state['progress'] == 0

    def test_message_content_in_state(self):
        """Parsed message is stored in state"""
        state = new_state()
        parse_line("Folder     3/5 [Sent]  -> [Sent]", state)
        assert "Syncing folder 3/5" in state['message']


# ==========================================
# 7. kill_sync Tests
# ==========================================

class TestKillSync:
    """Tests for process termination logic"""

    def test_kill_sync_nonexistent_process(self):
        """kill_sync for non-registered mailbox returns False"""
        from worker import kill_sync
        result = kill_sync(99999)
        assert result is False

    def test_kill_sync_registered_process(self):
        """kill_sync for registered process calls terminate"""
        from worker import kill_sync, active_processes

        # Create a mock process
        mock_process = MagicMock()
        active_processes[12345] = mock_process

        result = kill_sync(12345)
        assert result is True
        mock_process.terminate.assert_called_once()

        # Cleanup
        if 12345 in active_processes:
            del active_processes[12345]

    def test_kill_sync_process_terminate_error(self):
        """kill_sync handles process.terminate() exception"""
        from worker import kill_sync, active_processes

        mock_process = MagicMock()
        mock_process.terminate.side_effect = ProcessLookupError("No such process")
        active_processes[11111] = mock_process

        result = kill_sync(11111)
        assert result is False

        # Cleanup
        if 11111 in active_processes:
            del active_processes[11111]


# ==========================================
# 8. Full Sync Simulation
# ==========================================

class TestFullSyncSimulation:
    """End-to-end simulation of imapsync log parsing"""

    def test_complete_sync_flow(self):
        """Simulate a complete sync with 3 folders"""
        state = new_state()

        # Folder 1: INBOX with 50 messages
        parse_line("Folder     1/3 [INBOX]  -> [INBOX]", state)
        assert state['progress'] == 0

        parse_line("Host1: folder [INBOX] has 50 messages in total", state)
        parse_line("msg INBOX/25 {2048} copied", state)
        assert state['progress'] == 16  # (0 + 25/50/3)*100 ≈ 16

        parse_line("msg INBOX/50 {1024} copied", state)
        assert state['progress'] == 33  # (0 + 50/50/3)*100 ≈ 33

        # Folder 2: Sent with 20 messages
        parse_line("Folder     2/3 [Sent]  -> [Sent]", state)
        assert state['progress'] == 33  # (1/3)*100 ≈ 33

        parse_line("Host1: folder [Sent] has 20 messages in total", state)
        parse_line("msg Sent/20 {512} copied", state)
        assert state['progress'] == 66  # (1/3 + 20/20/3)*100 ≈ 66

        # Folder 3: Trash with 10 messages
        parse_line("Folder     3/3 [Trash]  -> [Trash]", state)
        assert state['progress'] == 66  # (2/3)*100 ≈ 66

        parse_line("Host1: folder [Trash] has 10 messages in total", state)
        parse_line("msg Trash/10 {256} copied", state)
        assert state['progress'] == 100  # (2/3 + 10/10/3)*100 ≈ 100 (clamped)

        # Transfer complete
        parse_line("Total bytes transferred : 987654321", state)
        assert state['bytes_transferred'] == 987654321

    def test_sync_with_empty_folders(self):
        """Simulate sync where some folders have no messages"""
        state = new_state()

        parse_line("Folder     1/3 [INBOX]  -> [INBOX]", state)
        parse_line("Host1: folder [INBOX] has 100 messages in total", state)
        parse_line("msg INBOX/100 {2048} copied", state)
        assert state['progress'] == 33  # (0 + 100/100/3)*100 ≈ 33

        # Empty folder (0 messages)
        parse_line("Folder     2/3 [Empty]  -> [Empty]", state)
        assert state['progress'] == 33  # (1/3)*100 ≈ 33
        parse_line("Host1: folder [Empty] has 0 messages in total", state)
        # No message lines for this folder

        parse_line("Folder     3/3 [Sent]  -> [Sent]", state)
        assert state['progress'] == 66  # (2/3)*100 ≈ 66
