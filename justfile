generate:
    uv run src/main.py pdf

regenerate input:
    uv run src/main.py pdf --regenerate='{{input}}'

clean-input:
    rm -rf input/*

clean-output:
    rm -rf output/*

clean: clean-input clean-output
