import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_split_file_name_extension_dot():
	from src.functions import splitFileNameExtension
	r = splitFileNameExtension("hello.py")
	assert r["name"] == "hello"
	assert r["extension"] == "py"

def test_split_file_name_extension_no_dot():
	from src.functions import splitFileNameExtension
	r = splitFileNameExtension("hello")
	assert r["name"] == ""
	assert r["extension"] == ""

def test_split_file_name_extension_multiple_dots():
	from src.functions import splitFileNameExtension
	r = splitFileNameExtension("a.b.c.txt")
	assert r["name"] == "abc"
	assert r["extension"] == "txt"

def test_crc32b_known():
	from src.functions import crc32b
	assert crc32b("hello") == "3610a686"

def test_crc32b_empty():
	from src.functions import crc32b
	assert crc32b("") == "0"

def test_urlencode():
	from src.functions import urlencode
	assert urlencode("a b") == "a%20b"
	assert urlencode("x=y") == "x%3Dy"

def test_rmatch_match():
	from src.functions import rmatch
	assert rmatch("abc123", r"^[a-z]+\d+$") is not False

def test_rmatch_no_match():
	from src.functions import rmatch
	assert rmatch("123abc", r"^[a-z]+\d+$") is False

def test_pmatch_simple():
	from src.functions import pmatch
	r = pmatch("hello 42 world", r"\d+")
	assert r == ["42"]

def test_fwrite_fread(tmp_path):
	from src.functions import fwrite, fread
	fp = str(tmp_path / "test.txt")
	fwrite(fp, "hello", overwrite=True)
	assert fread(fp) == "hello"

def test_fwrite_append(tmp_path):
	from src.functions import fwrite, fread
	fp = str(tmp_path / "append.txt")
	fwrite(fp, "line1\n", overwrite=True)
	fwrite(fp, "line2\n", overwrite=False)
	content = fread(fp)
	assert "line1" in content
	assert "line2" in content

def test_fread_missing():
	from src.functions import fread
	assert fread("/tmp/nonexistent_file_xyz") is False

def test_importmodule_reload():
	from src.functions import importmodule
	mod = importmodule("config", rel=False, opts={"path": ""})
	assert mod is not False
	assert hasattr(mod, "Options")
