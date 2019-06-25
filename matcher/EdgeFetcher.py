import openreview.tools

class EdgeFetcher:

    def __init__ (self, or_client):
        self.or_client = or_client

    def get_all_edges (self,  inv_id):
        return openreview.tools.iterget_edges(self.or_client, invitation=inv_id, limit=50000)
