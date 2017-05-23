# openreview-matching

To install: clone the repo, navigate to the directory, and run `pip install .`

This package requires `gurobipy`, the python interface of the [Gurobi](http://www.gurobi.com/) optimization package.

## Expertise Modeling

A training and evaluation pipeline for expertise models.

In this pipeline, there are Models and Evaluators. Models can be trained and tested, and
Evaluators are used to evaluate them. The file `main.py` runs the pipeline with the parameter options below.

You can create your own Models and Evaluators by extending the abstract base classes
in `/eval/base_evaluator` and `/model/base_model`

See `/model/README.md` or `/eval/README.md` for more information.

### Example usage:

Train the `tfidf` and `randomize` models on `train.json`, evaluate using the `recall_at_m` evaluator,
predict rankings using `test.json`, then save the models:

`python main.py -m tfidf randomize -e recall_at_m -f data/train.json -p datascripts/test.json -s`

Load serialized `tfidf` model and evaluate again:

`python main.py -m tfidf -e recall_at_m -p data/test.json`

Retrain `randomize` model:

`python main.py -m randomize -f data/train.json`

See the comments in `main.py` for a detailed explanation of each argument.
