# Evaluators

To add a new evaluator to the pipeline, create a new directory under `/eval` with two
files: an `__init__.py` file, and a file with the evaluator code in it. The evaluator
file must have the same name as the directory.


```
/eval
  /my_evaluator
    __init__.py
    my_evaluator.py

```

`my_evaluator.py` should contain a class called `Evaluator` which extends `base_evaluator.Evaluator`
You should define one method called `evaluate()`. It's important that this function adheres to the
base evaluator's API. See `/eval/base_evaluator/evaluator.py` for details.

```
class Evaluator(base_evaluator.Evaluator):
    def __init__(self):
        # initialize the evaluator

    def evaluate(self, ranklists):
        # evaluate the ranked lists

```

`__init__.py` should contain the following code:

```
from my_evaluator import *
```
