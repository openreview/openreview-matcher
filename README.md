# openreview-matcher

A package for finding sets of matches between papers and reviewers, subject to constraints and affinity scores.

Frames the task of matching papers to reviewers as a [network flow problem](https://developers.google.com/optimization/assignment/assignment_min_cost_flow).

`/matcher` contains the matcher module that implements the flow `Solver` class, as well as an `Encoder` class designed for encoding metadata from OpenReview into a cost matrix that can be interpreted by the `Solver`.

`/webserver` contains a Flask app that implements a REST API for solving paper-reviewer assignments. It's primarily intended to be used via the OpenReview web interface.
