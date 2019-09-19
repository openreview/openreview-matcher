[![CircleCI](https://circleci.com/gh/iesl/openreview-matcher.svg?style=svg)](https://circleci.com/gh/iesl/openreview-matcher)

# OpenReview Matcher

A web service for finding sets of matches between papers and reviewers, subject to constraints and affinity scores, designed for integration with the OpenReview web application.

Frames the task of matching papers to reviewers as a [network flow problem](https://developers.google.com/optimization/assignment/assignment_min_cost_flow).

This is implemented as a Flask RESTful service.   Structure of the project:

'/matcher' contains the python code that implements app including:

'/matcher/app.py' the main app that is run when Flask starts.  Initializes the app.

'/matcher/routes.py' functions that  serve as the endpoints of the service e.g

'/matcher/match.py' contains the task function compute_match which runs the match solver in a thread

'/matcher/assignment_graph/AssignmentGraph.py' Defines a class which wraps the algorithm/library for solving the assignment problem.

## Configuration of the app

Two config.cfg files are read in.  The first is in the top level directory.  It can contain
settings that are use for the app.   A second file is read in from instance/ directory which should
contain settings particular to a users environment.  Those settings will override ones that
were set in the first file.  Settings that are necessary:
OPENREVIEW_BASEURL, LOG_FILE


## Starting the Flask server

From the top level project directory, run the following:

```
export FLASK_APP=matcher/app.py
flask run
```

By default, the app will run on localhost:5000.

## Testing

http://localhost:5000/match/test should show a simple page indicating that Flask is running

**Testing with pytest:**

We have three test suites below.  The end-to-end test suite relies on running the OR service with a clean database
and the clean_start_app.  The other two test suites do not need this.

All tests may be run by doing the following:

    cd openreview
    export NODE_ENV=circleci
    node scripts/clean_start_app.js
    cd openreview-matcher
    source venv/bin/activate
    python -m pytest tests

Note:  Each time you run the test suite clean_start_app must be run to start with a clean db.

**End to End Test Suite**

tests/test_end_to_end.py is a test suite that tests all aspects of the matcher.

**Instructions for running this test case with pytest**

This requires running a clean (empty mongo db).  This can be done by running
a local OpenReview service using its scripts/clean_start_app.js with the environment var:
NODE_ENV=circleci like:

    export NODE_ENV=circleci
    node scripts/clean_start_app.js

Note: The clean_start_app must be restarted each time before running the end_to_end tests.

To run the end-to-end test suite:

1. cd to openreview-matcher root directory.
1. Go into the virtual environment for running the matcher (e.g. ```source venv/bin/activate```)
1. ```python -m pytest tests/test_end_to_end.py ```


**Matcher Unit Tests**

tests/test_solver.py contains unit tests to check the AssignmentGraph interface to the Google OR library.
It sends the flow solver inputs that are representative of common situations within OpenReview.   Verifies that
the algorithm finds optimal solutions and respects constraints between users and papers.

To run the unit tests:

1. Cd to openreview-matcher root directory.
1. Go into virtual environment for running matcher (e.g. ```source venv/bin/activate```)
1. ```python -m pytest tests/test_solver.py```

**Integration tests**

 test_match_service is a set of integration tests produce the variety of error conditions that result from passing the
 matcher incorrect inputs.

 A known issue during integration testing:  This app logs to both the console and a file.
 During testing Flask sets the console logging level to ERROR
 Many tests intentionally generate errors and exceptions which means
 they will be logged to the console.  Thus the console during error
 testing will NOT JUST SHOW "OK" messages.  There will be exception stack traces
 shown because of the error logger.

To run the integration tests:

1. Cd to openreview-matcher root directory.
1. Go into virtual environment for running matcher (e.g. ```source venv/bin/activate```)
1. ```python -m pytest tests/test_match_service.py```



