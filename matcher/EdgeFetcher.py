import openreview.tools
from collections import defaultdict
import openreview

class EdgeFetcher:

    def __init__ (self, or_client):
        self.or_client = or_client

    def get_all_edges (self, inv_id):
        edges = []
        offset = 0
        while True:
            edges_grouped_by_paper = self.or_client.get_grouped_edges(inv_id,groupby='head',select='tail,label,weight', limit=1000, offset=offset)
            offset += 1000
            self._parse_json_to_edges(edges, inv_id, edges_grouped_by_paper)
            if len(edges_grouped_by_paper) < 1000:
                break
        return edges

    def _parse_json_to_edges (self, edge_list, inv, edges_grouped_by_paper):
        for group in edges_grouped_by_paper:
            forum_id = group['id']['head']
            values = group['values']
            for v in values:
                edge_list.append(self._create_edge(inv, forum_id, v))


    def _create_edge (self, inv, head, fields):
        return openreview.Edge(invitation=inv,head=head, tail=fields['tail'], weight=fields.get('weight'),
                               label=fields.get('label'), readers=[], writers=[], signatures=[])



