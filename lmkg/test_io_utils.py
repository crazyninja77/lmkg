import os
import yaml
import pytest
from unittest.mock import patch

from lmkg.io_utils import (
    list_source_files,
    ensure_copy_exists,
    get_section_words,
    get_next_task,
    save_qid
)

@pytest.fixture
def mock_env(tmp_path):
    """
    Sets up temporary source and output directories and mocks the global
    constants in io_utils so tests don't touch real project files.
    """
    datasets_dir = tmp_path / "datasets"
    output_dir = tmp_path / "output"
    datasets_dir.mkdir()
    
    with patch("lmkg.io_utils.DATASETS_DIR", str(datasets_dir)), \
         patch("lmkg.io_utils.OUTPUT_DIR", str(output_dir)), \
         patch("lmkg.io_utils.BANNED_KEYS", {"mapping", "target"}):
        yield datasets_dir, output_dir

def test_list_source_files(mock_env):
    datasets_dir, _ = mock_env
    
    # Create dummy files
    (datasets_dir / "test1.yaml").touch()
    (datasets_dir / "test2.txt").touch() # Should be ignored
    
    files = list_source_files()
    assert len(files) == 1
    assert files[0].endswith("test1.yaml")

def test_ensure_copy_exists_migrates_lists(mock_env):
    datasets_dir, _ = mock_env
    source_file = datasets_dir / "test.yaml"
    
    # Create a source YAML file with a list instead of a dict
    yaml_data = {
        "case_1": {
            "input": {
                "base": ["amsterdam", "mapping", "netherlands"]
            }
        }
    }
    with open(source_file, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f)
        
    out_path = ensure_copy_exists(str(source_file))
    
    assert os.path.exists(out_path)
    
    # Verify it converted the list to a dict mapped to None, ignoring banned keys
    with open(out_path, "r", encoding="utf-8") as f:
        copied_data = yaml.safe_load(f)
        
    base_words = copied_data["case_1"]["input"]["base"]
    assert "mapping" not in base_words
    assert base_words == {"amsterdam": None, "netherlands": None}

def test_get_section_words():
    inp = {"base": ["word1", "mapping", "word2"]} 
    with patch("lmkg.io_utils.BANNED_KEYS", {"mapping"}):
        words = get_section_words(inp, "base")
        assert words == {"word1": None, "word2": None}

def test_save_qid(mock_env):
    _, output_dir = mock_env
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / "test.yaml"
    
    yaml_data = {"case_1": {"input": {"base": {"amsterdam": None}}}}
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f)
        
    save_qid(str(out_file), "case_1", "base", "amsterdam", "Q5462")
    
    with open(out_file, "r", encoding="utf-8") as f:
        updated_data = yaml.safe_load(f)
        
    assert updated_data["case_1"]["input"]["base"]["amsterdam"] == "Q5462"