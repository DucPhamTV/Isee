.PHONY: env check clean
env:
	pip install -r requirements.txt

check:
	#pylint **/*.py
	flake8 --exclude=env/

clean:
	rm -r env/
