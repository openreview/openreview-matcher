# openreview-matching

A module for computing paper-reviewer matches in OpenReview. Supports all stages of the reviewer matching process, including metadata creation, feature definitions, and optimizing with constraints. Also supports the training, testing, and evaluation of various (custom) models of reviewer expertise, which may then be used as a feature for matching.

## Installation
This package is not available on pip. To install, clone this repository, and run `pip install <openreview-matching directory>`

This package requires `gurobipy`, the python interface of the [Gurobi](http://www.gurobi.com/) optimization package. You can get a free license with an academic email address.

## Training and Evaluating Models

This package supports a training and evaluation pipeline for custom expertise models. In this pipeline, there are Models and Evaluators. Models can be trained and tested, and Evaluators are used to evaluate them. The file `main.py` runs the pipeline. Parameters can be found in the docstring of `main.py`.

You can create your own Models and Evaluators by extending the abstract base classes
in `openreview_matcher/evals/base_evaluator` and `openreview_matcher/models/base_model`

See `openreview_matcher/models/README.md` or `openreview_matcher/evals/README.md` for more information.

### Example usage:

Train the `tfidf` and `randomize` models on `train.json`, using the reviewer archives defined in `archive.json`. Evaluate using the `recall_at_m` evaluator, and predict rankings using the data in `test.json`. Then save the models:

`python main.py --models tfidf randomize --archive archive.json --fit data/train.json --predict datascripts/test.json --evals recall_at_m --save`

Load serialized `tfidf` model and evaluate again:

`python main.py --models tfidf --predict data/test.json --evals recall_at_m`

See the comments in `main.py` for a detailed explanation of each argument.
