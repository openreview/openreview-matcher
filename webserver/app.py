from flask import Flask, request
from threading import Thread
import queue
import json
import time

import openreview
import matcher


app = Flask(__name__)

def run_match(config_note, client):
    start_time = time.time()
    config = config_note.content
    metadata = list(openreview.tools.iterget_notes(client, invitation=config['metadata_invitation']))
    reviewer_group = client.get_group(config['match_group'])
    paper_notes = list(openreview.tools.iterget_notes(client, invitation=config['paper_invitation']))
    assignment_inv = client.get_invitation(config['assignment_invitation'])

    reviewer_ids = reviewer_group.members

    # This could be set by hand if reviewers or papers have specific supplies/demands
    supplies = [config['max_papers']] * len(reviewer_ids)
    demands = [config['max_users']] * len(metadata)

    # enter 'processing' phase
    config_note.content['status'] = 'processing'
    config_note = client.post_note(config_note)

    print('clearing existing assignments...')
    clear_time = time.time()
    for assignment_note in openreview.tools.iterget_notes(client, invitation=assignment_inv.id):
        client.delete_note(assignment_note)
    print('took {0:.2f} seconds'.format(time.time() - clear_time))

    # instantiate the metadata encoder, and use it to instantiate a flow solver
    print('instantiating encoder and solver...')
    instantiate_time = time.time()
    encoder = matcher.metadata.Encoder(metadata, config, reviewer_ids)
    flow_solver = matcher.Solver(supplies, demands, encoder.cost_matrix, encoder.constraint_matrix)
    print('took {0:.2f} seconds'.format(time.time() - instantiate_time))

    print('finding solution...')
    solution_time = time.time()
    solution = flow_solver.solve()
    print('took {0:.2f} seconds'.format(time.time() - solution_time))

    # decode the solution matrix
    print('decoding solution...')
    decoding_time = time.time()
    assignments_by_forum, alternates_by_forum = encoder.decode(solution)
    print('took {0:.2f} seconds'.format(time.time() - decoding_time))

    print('posting assignments...')
    posting_time = time.time()
    for forum, assignments in assignments_by_forum.items():
        client.post_note(openreview.Note.from_json({
            'forum': forum,
            'invitation': assignment_inv.id,
            'replyto': forum,
            'readers': assignment_inv.reply['readers']['values'],
            'writers': assignment_inv.reply['writers']['values'],
            'signatures': assignment_inv.reply['signatures']['values'],
            'content': {
                'label': config['label'],
                'assignedGroups': assignments,
                'alternateGroups': []
            }
        }))
    print('took {0:.2f} seconds'.format(time.time() - posting_time))

    config_note.content['status'] = 'complete'
    client.post_note(config_note)
    print('done. total time: {0:.2f} seconds'.format(time.time() - start_time))

@app.route('/match', methods=['POST', 'OPTIONS'])
def match():
    print('matching')

    client = openreview.Client()

    config_note = client.get_note(request.form['configNoteId'])
    config_note.content['status'] = 'queued'
    config_note = client.post_note(config_note)

    args = (config_note, client)

    match_thread = Thread(
        target=run_match,
        args=args
    )
    match_thread.start()

    return 'matching done'

if __name__ == '__main__':
    app.run()
