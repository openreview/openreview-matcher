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

    def get_all_edges (self, inv_id):
        d = defaultdict(list)
        offset = 0
        while True:
            edges_grouped_by_paper = self.or_client.get_edges_group(inv_id,groupby='head',select='tail,label,weight', limit=1000, offset=offset)
            offset += 1000
            self.parse_json_to_edges(d, inv_id, edges_grouped_by_paper)
            if len(edges_grouped_by_paper) < 1000:
                break
        return d

    # Given an array of JSON objects where each object is like {id: {head: paper_id} values: [ {edge fields}, {edge fields} ]}
    # load it into the dict d keyed by the forum_id of the edge
    def parse_json_to_edges (self, d, inv, edges_grouped_by_paper):
        for group in edges_grouped_by_paper:
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