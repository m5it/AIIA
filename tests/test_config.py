import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_config_imports():
	from config import Options
	assert isinstance(Options, dict)

def test_config_has_key_keys():
	from config import Options
	for k in ["VERSION", "AI_MODEL", "MODE", "INSTRUCT_CLASS", "AI_MAX_ITERATIONS"]:
		assert k in Options, "Missing key: {}".format(k)

def test_config_default_mode():
	from config import Options
	assert Options["MODE"] in ("plan", "build")

def test_config_default_model():
	from config import Options
	assert isinstance(Options["AI_MODEL"], str)
	assert len(Options["AI_MODEL"]) > 0

def test_config_version_format():
	from config import Options
	parts = str(Options["VERSION"]).split(".")
	assert len(parts) == 3
