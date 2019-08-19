[![CircleCI](https://circleci.com/gh/iesl/openreview-matcher.svg?style=svg&circle-token=d20a11c2cb9e46d2a244638d1646ebdf3aa56b39)](https://circleci.com/gh/iesl/openreview-matcher)

# OpenReview Matcher

A web service for finding ideal matches between papers and reviewers, subject to constraints and affinity scores, and designed for integration with the OpenReview web application.

The OpenReview Matcher is implemented as a Flask RESTful API.

## Installation
Coming soon.

## Configuration of the app
Coming soon.


## Starting the Flask server

From the top level project directory, run the following:

```
export FLASK_APP=matcher
flask run
```

By default, the app will run on `http://localhost:5000`.

## Testing

`http://localhost:5000/match/test` should show a simple page indicating that Flask is running.

### Unit Tests (pytest)

The entire suite of unit and integration tests can be run with the following commands from the top level project directory:

    export OPENREVIEW_HOME=<path_to_openreview>
    python -m pytest tests

Individual test modules can be run in the same way:

	export OPENREVIEW_HOME=<path_to_openreview>
	python -m pytest tests/test_integration

For integration tests with the OpenReview server application, a [test fixture](https://docs.pytest.org/en/latest/fixture.html) is executed that starts a clean, empty OpenReview instance and creates a mock conference. When running tests that use the `test_context` fixture, ensure that no other OpenReview instances are running in the background.


