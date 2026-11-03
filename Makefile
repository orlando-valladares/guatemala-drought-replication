.PHONY: all figures site test clean

all: figures site test

figures:
	python3 code/python/build_figures.py

site: figures
	cp out/figures/pdf/*.pdf docs/figures/
	cp out/figures/png/*.png docs/figures/
	cp out/report/Guatemala_Drought_Draft.pdf docs/downloads/

test:
	python3 tests/test_release.py

clean:
	find out/figures -type f \( -name '*.pdf' -o -name '*.png' \) -delete
