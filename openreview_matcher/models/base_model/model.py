import abc
from openreview_matcher import utils

class Model(object):
    """
    A Model implements an expertise model (for example, tfidf).

    Models must implement the fit(), build_archive(), and predict methods.

    For examples, see:
        models/randomize/randomize.py
        models/tfidf/tfidf.py

    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def fit(self, train_data, archive_data):
        """
        Fit the model to the data.

        Arguments
            @train_data: an iterator over records (dicts) that contains the training data.
            Records must have a "content" field containing a string and a "forum" field
            containing the record's forum ID.

            @archive_data: an iterator over records (dicts) that contains each reviewer's
            archive. Records must have a "content" field containing a string representing
            the archive, and a "reviewer_id" field with the reviewer's OpenReview ID.

        Returns
            None

        """

        for record in train_data:
            pass

    @abc.abstractmethod
    def predict(self, test_record):
        """
        predict() should return a list of openreview user IDs, in descending order by
        expertise score in relation to the test record.

        Arguments
            @test_record: a note record (dict) representing the note to rank against.

            Testing records should have a "forum" field. This means that the record
            is identified in OpenReview by the ID listed in that field.

        Returns
            a list of reviewer IDs in descending order of expertise score

        """

        forum = test_record['forum']
        return []


    def serialize(self, outfile):
        """
        Arguments
            @outfile

        Returns
            None

        Side Effects
            Serializes the model
        """
        utils.save_obj(self, outfile)

