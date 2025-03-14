# create coverage data file
coverage:
	python3 coverage.py sample_test.py

# update json file
json:
	python3 .coverage_instrumented/sample_test.py

# generate report
report:
	python3 report.py sample_test.py

# clean
clean:
	rm -rf .coverage_instrumented
	rm -rf .coverage_data.json
