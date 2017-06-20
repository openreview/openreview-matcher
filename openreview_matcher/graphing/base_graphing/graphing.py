import abc


class Graphing(object):
    """
    A Graphing object implements a graph method
    that takes in a rank list and outputs a graph
    based on these ranks
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, params=None):
        pass

    @abc.abstractmethod
    def graph(self, ranklists, ax, model_name):
        """
        Arguments:
            @ranklist: A list of query ranks that includes the reviewer and their score for that query

        """
        pass
