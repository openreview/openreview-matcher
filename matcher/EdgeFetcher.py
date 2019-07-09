import openreview.tools
import requests
import os
from collections import defaultdict
from openreview import OpenReviewException, Edge
import openreview

class EdgeFetcher:

    def __init__ (self, or_client):
        self.or_client = or_client

    def get_all_edges_slow (self,  inv_id):
        return openreview.tools.iterget_edges(self.or_client, invitation=inv_id, limit=50000)

    # TODO This limit of 5000 allows the query to return a list of over 1000 groups.
    # This may get changed in the future which will mean doing a bunch of queries with offset by 1000
    def get_all_edges (self, inv_id):
        json = self.or_client.get_edges_group(inv_id,groupby='head',project='tail,label,weight', limit=5000)
        return self.parse_json_to_edges(inv_id, json)

    # The json returned will be an array of objects where each object is like {id: {head: paper_id} values: [ {edge fields}, {edge fields} ]}
    # Note: The edge fields included are the ones that mentioned in the "project" parameter to the request URL
    # Returns a dict where keys are the forum_ids and the values are lists of Edges
    def parse_json_to_edges (self, inv, json):
        d = defaultdict(list)
        for group in json:
            forum_id = group['id']['head']
            values = group['values']
            for v in values:
                d[forum_id].append(self.create_edge(inv, forum_id, v))
        return d

    def create_edge (self, inv, head, fields):
        return openreview.Edge(invitation=inv,head=head, tail=fields['tail'], weight=fields.get('weight'),
                               label=fields.get('label'), readers=[], writers=[], signatures=[])

    def __handle_response(self,response):
        try:
            response.raise_for_status()

            if("application/json" in response.headers['content-type']):
                if 'errors' in response.json():
                    raise OpenReviewException(response.json()['errors'])
                if 'error' in response.json():
                    raise OpenReviewException(response.json()['error'])

            return response
        except requests.exceptions.HTTPError as e:
            if 'errors' in response.json():
                raise OpenReviewException(response.json()['errors'])
            else:
                raise OpenReviewException(response.json())

def test_iclr ():
    password = 'acoldwindydayinamherst'
    base_url = 'http://openreview.localhost'
    client = openreview.Client(baseurl=base_url,
                     username='OpenReview.net', password=password)


    ef = EdgeFetcher(client)
    inv = 'ICLR.cc/2019/Conference/-/TPMS'
    edge_map = ef.get_all_edges2(inv)
    keys = list(edge_map.keys())
    k0 = keys[0]
    score_edges = edge_map[k0]
    print(len(score_edges))

# test_iclr()