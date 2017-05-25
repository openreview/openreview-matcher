import abc

class Evaluator(object):

    """
    An Evaluator implements an evaluation method (for example, recall_at_m).

    Evaluators must implement the evaluate() method.

    See eval/recall_at_m/recall_at_m.py for details.

    TODO: Decide on a structured way to pass data into evaluators.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, params=None):
        self.data = data

    @abc.abstractmethod
    def evaluate(self, ranklists):
        """
        Arguments
            @ranklists: A list of tuples.
            The 0th index of the tuple contains the forum ID of the rank list being evaluated.
            The 1st index of the tuple contains a list of reviewer IDs, in order of expertise score.

        Returns
            a generator object that yields a forum and an array of scores for each ranked list. If
            only one score is needed, return the score in an array by itself.


        """
        pass

