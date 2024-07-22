install: install
	pip install -r requirements.txt

run: run
	python -m src.main --host 127.0.0.1 --port 5000
