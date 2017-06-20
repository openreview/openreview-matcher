import abc


class KeyphraseExtractor(object):
    """
    A Keyphrase Extractor object implements a extract method that 
    returns the 'best' keywords in a certain document
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, params=None):
        pass

    @abc.abstractmethod
    def extract(self, document, top_n=10, corpus=None):
        """
        Arguments:
            @document: the string to perform keyphrase extraction  
            @top_n: the number of top words to get
            @corpus: a list of documents representing the corpus
        """
        pass
