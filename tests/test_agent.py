"""Tests for AutoFixAgent"""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agent import AutoFixAgent

def test_agent_run_scan_only(tmp_path):
    """Test agent scan without auto-fix"""
    test_file = tmp_path / "test.py"
    test_file.write_text("def test(): pass")
    
    agent = AutoFixAgent(force_rescan=True)
    result = agent.run(str(tmp_path), auto_fix=False)
    
    assert "scanned_files" in result
    assert "files_with_issues" in result
    assert "issues_found" in result
    assert result["files_fixed"] == 0

def test_agent_run_with_autofix(tmp_path):
    """Test agent with auto-fix enabled"""
    test_file = tmp_path / "test.py"
    test_file.write_text("x == None")
    
    agent = AutoFixAgent(force_rescan=True)
    result = agent.run(str(tmp_path), auto_fix=True)
    
    assert "scanned_files" in result
    assert "files_fixed" in result
    assert "fixes_applied" in result

def test_agent_handles_empty_directory(tmp_path):
    """Test agent with empty directory"""
    agent = AutoFixAgent(force_rescan=True)
    result = agent.run(str(tmp_path), auto_fix=False)
    
    assert result["scanned_files"] == 0
    assert result["files_with_issues"] == 0
