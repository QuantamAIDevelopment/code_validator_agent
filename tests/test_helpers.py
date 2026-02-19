"""Tests for helper modules"""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from helpers.zip_helper import ZipHelper
import zipfile
import os

def test_zip_helper_extract(tmp_path):
    """Test ZIP extraction"""
    zip_path = tmp_path / "test.zip"
    extract_dir = tmp_path / "extracted"
    
    # Create test ZIP
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(test_file, "test.txt")
    
    result = ZipHelper.extract_zip(str(zip_path), str(extract_dir))
    assert os.path.exists(result)

def test_zip_helper_create(tmp_path):
    """Test ZIP creation"""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("content")
    
    output_zip = tmp_path / "output.zip"
    files_added = ZipHelper.create_zip(str(source_dir), str(output_zip))
    
    assert files_added == 1
    assert output_zip.exists()
