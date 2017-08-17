from openreview_matcher.eval_data import base_eval_data
from operator import itemgetter

from openreview_matcher import utils


class EvalData(base_eval_data.EvalData):
    """
    A EvalData object that wraps around the bids dataset (bids)
    """

    def __init__(self, eval_data_location):
        self.eval_data = utils.load_obj(eval_data_location)

        print(type(self.eval_data))

    def get_eval_by_forum(self, forum_id):
        """ 
        Returns the evaluation data for the forum id 
        
        e.g returns all of the bids for a forum
        """

        bids_by_forum_id = self.eval_data[forum_id] 
        return [{"signature": bid.signatures[0], "bid": bid.tag} for bid in bids_by_forum_id]        

    def get_pos_bids_for_forum(self, forum_id):
        """ Get all of the pos bids for a forum """

        positive_labels = ['I want to review', 'I can review']
        forum_bids = self.get_eval_by_forum(forum_id) 
        return [bid for bid in forum_bids if bid["bid"] in positive_labels]

    def reviewer_has_bid(self, reviewer_id, forum_id):
        """ Returns True if the reviewer bid on that 'paper' """

        paper_bids = self.get_eval_by_forum(forum_id)

        # some papers don't have any bids
        if len(paper_bids) == 0:
            return False

        has_bid = [True if bid["signature"] == reviewer_id.decode("utf-8") else False for bid in paper_bids][0]
        return has_bid

    def get_bid_for_reviewer_paper(self, reviewer_id, forum_id):
        """ 
        Gets the bid for the reviewer and the paper 
        Returns 0 if the bid is not relevant and 1 if the bid is relevant

        Relevance is defined by if the reviewer wants to review or can reviewer and non
        relevant is otherwise
        """

        positive_labels = ['I want to review', 'I can review']
        paper_bids = self.get_eval_by_forum(forum_id)
        bid_value = [1 if bid["bid"] in positive_labels else 0 for bid in paper_bids if
                     bid["signature"] == reviewer_id.decode('utf-8')]
        if len(bid_value) > 0:
            return bid_value[0]
        else:
            return 0