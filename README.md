[![CircleCI](https://circleci.com/gh/iesl/openreview-matcher.svg?style=svg&circle-token=d20a11c2cb9e46d2a244638d1646ebdf3aa56b39)](https://circleci.com/gh/iesl/openreview-matcher)

# OpenReview Matcher
A simple Flask web service for finding optimal paper-reviewer assignments for peer review, subject to constraints and affinity scores, and designed for integration with the OpenReview server application.

## Installation
Coming soon.

## Configuration of the app

The default configuration is placed in config.cfg inside of the root folder, if you want to use a different configuration you need to set an environment variable with the path to the file

```
export MATCHER_CONFIG=[path_to_config_file]
```


## Starting the Flask server
From the top level project directory, run the following:

```
export FLASK_APP=matcher/service
flask run
```

By default, the app will run on `http://localhost:5000`. The endpoint `/match/test` should show a simple page indicating that Flask is running.

## Unit & Integration Tests (with pytest)

The `/tests` directory contains unit tests and integration tests (i.e. tests that communicate with an instance of the OpenReview server application), written with [pytest](https://docs.pytest.org/en/latest).

### Requirements

Running the tests requires MongDB and Redis to support the OpenReview server instance used in the integration tests.

Before running integration tests, ensure that `mongod` and `redis-server` are running, and that no existing OpenReview instances are active.

Integration tests use the `test_context` [pytest fixture](https://docs.pytest.org/en/latest/fixture.html), which starts a clean, empty OpenReview instance and creates a mock conference.

### Running the Tests

The entire suite of tests can be run with the following commands from the top level project directory:

    export OPENREVIEW_HOME=<path_to_openreview>
    python -m pytest tests

Individual test modules can be run by passing in the module file as the argument:

	export OPENREVIEW_HOME=<path_to_openreview>
	python -m pytest tests/test_integration.py


