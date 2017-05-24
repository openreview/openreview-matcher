# Models

To add a new model to the pipeline, create a new directory under `/models` with two
files: `__init__.py` file, and a file with the model code in it. The model file must
have the same name as the directory.

```
/models
	/my_model
		__init__.py
		my_model.py

```

`my_model.py` should contain a class called `Model` which extends `base_model.Model`
You should define two methods: `fit()` and `predict()`. It's
important that these three functions adhere to the base model's API. See
`/models/base_model/model.py` for details.


`__init__.py` should contain the following code:

```
from my_model import *
```
