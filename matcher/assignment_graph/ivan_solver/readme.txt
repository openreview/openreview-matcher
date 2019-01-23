The python class auto_assigner in autoassigner.py implements the PeerReview4All algorithm (PR4A) of the paper "PeerReview4All: Fair and Accurate Reviewer Assignment in Peer Review" by Ivan Stelmakh, Nihar Shah and Aarti Singh.

DEPENDENCIES:
This code uses the gurobipy package in python for solving the Linear Programming problems. Gurobi offers free academic licenses for universities. To obtain your license, please go to http://www.gurobi.com/academia/for-universities and follow the instructions provided there.

INPUTS:
'simmatrix' is an n x m matrix with entries in {-1}U[0, 1], where n = number of reviewers, m = number of papers and any conflict of interest is handled by setting the corresponding entry to -1 . 'demand' is a number of reviewers required per paper and 'ability' is a maximum number of papers that reviewer can review.'function' is any monotonically increasing function (identity by default) of similarities which defines the notion of fairness.

HOWTO
The entry point of the class is the function 'fair_assignment' which takes 'mode' as an argument. If 'mode' == "full", then the full version of the algorithm is called. If 'mode' == "fast", then only one iteration of the algorithm is conducted (fairness and statistical results are guaranteed, but assignment is not optimized for the second worst-off paper and so on). 

OUTPUT:
A dictionary of the form {paper: [assigned_reviewers]} that encodes the resulting assignment.

EXAMPLE:
A minimum working example is constructed in working_example.ipynb