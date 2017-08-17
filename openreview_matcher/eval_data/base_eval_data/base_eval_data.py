import abc
from openreview_matcher import utils



class EvalData(object):
    """
    A EvalData object that wraps around the evaluation dataset (bids, subject area) 
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, eval_data_location):
        self.eval_data = utils.load_obj(eval_data_location)

    @abc.abstractmethod
    def get_eval_by_forum(self, forum_id):
        """ 
        Returns the evaludation data for the forum id 
        e.g returns all of the bids for a forum
        """

        pass
