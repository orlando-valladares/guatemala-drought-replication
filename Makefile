.PHONY: all reproduce test check-release

all: reproduce test check-release

reproduce:
	python3 scripts/build_derived_outputs.py

test:
	python3 tests/test_reproduction.py

check-release:
	python3 scripts/check_release.py
