test:
	python3 setup.py build_ext --inplace
	python3 test.py
dist:
	rm -f dist/*
	python3 setup.py sdist bdist_wheel
upload:
	twine upload dist/*