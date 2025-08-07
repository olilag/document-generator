generate:
    uv run src/main.py

clean-input:
    rm -rf input/*

clean-output:
    rm -rf output/*

clean: clean-input clean-output
