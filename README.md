# openreview-matcher

A package for finding sets of matches between papers and reviewers, subject to constraints and affinity scores.

Frames the task of matching papers to reviewers as a [network flow problem](https://developers.google.com/optimization/assignment/assignment_min_cost_flow).

This is implemented as a Flask RESTful service.   Structure of the project:

'/matcher' contains the python code that implements app including:

'/matcher/assign_reviewers.py' the main function that is run when Flask starts.  Initializes the app.

'/matcher/routes.py' functions that  serve as the endpoints of the service e.g
 
'/matcher/assign.py' contains the task function run_match which runs the match solver in a thread

'/matcher/solver.py' Defines the Solver class which wraps the min_net_flow solver

**Configuration of the app**

Two config.cfg files are read in.  The first is in the top level directory.  It can contain
settings that are use for the app.   A second file is read in from instance/ directory which should
contain settings particular to a users environment.  Those settings will override ones that
were set in the first file.  


**Testing:**

 test_match is a set of integration tests.  They use a flask test_client which invokes
 the Flask server with TESTING=True.   The server switches to using tests.MockORClient if TESTING=True.
 Otherwise, it uses the openreview.Client to communicate with OpenReview.
 
 A known issue during integration testing:  This app logs to both the console and a file.
 During testing Flask sets the console logging level to ERROR
 Many tests intentionally generate errors and exceptions which means
 they will be logged to the console.  Thus the console during error
 testing will NOT JUST SHOW "OK" messages.  There will be exception stack traces
 shown because of the error logger. 
 
 test_solver is a single unit test that runs the solver on a simple matrix.

**To run it:**

From Intellij IDEA:

There is a pre-built run/debug configurations:  _assign_reviewers_ should be used to 
run the app during development and debugging. 

From the command line:

source venv/bin/activate
export FLASK_APP=matcher/assign_reviewers.py
flask run