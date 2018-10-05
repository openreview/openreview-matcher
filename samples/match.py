import openreview
import matcher
import argparse
import json
import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--baseurl', help="openreview base URL")
    parser.add_argument('--username')
    parser.add_argument('--password')

    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    ## Initialize the client library with username and password
    client = openreview.Client(baseurl=args.baseurl, username=args.username, password=args.password)
    print("connecting to", client.baseurl)

    # network calls
    print('collecting data...')
    collection_time = time.time()
    submission_inv = client.get_invitation(config['paper_invitation'])
    metadata = list(openreview.tools.iterget_notes(client, invitation=config['metadata_invitation']))
    reviewers_group = client.get_group(config['match_group'])
    reviewer_ids = reviewers_group.members
    papers_by_forum = {p.forum: p for p in openreview.tools.iterget_notes(client, invitation=submission_inv.id)}
    assignment_inv = client.get_invitation(config['assignment_invitation'])
    config_inv = client.get_invitation(config['config_invitation'])
    print("took {0:.2f} seconds".format(time.time() - collection_time))

    # This could be set by hand if reviewers or papers have specific supplies/demands
    supplies = [config['max_papers']] * len(reviewer_ids)
    demands = [config['max_users']] * len(metadata)

    print('clearing existing assignments, and clearing config with label="{}" ...'.format(config['label']))
    clear_time = time.time()
    for config_note in openreview.tools.iterget_notes(client, invitation=config_inv.id):
        if config_note.content['label'] == config['label']:
            client.delete_note(config_note)

    for assignment_note in openreview.tools.iterget_notes(client, invitation=assignment_inv.id):
        if assignment_note.content['label'] == config['label']:
            client.delete_note(assignment_note)
    print('took {0:.2f} seconds'.format(time.time() - clear_time))


    # instantiate the metadata encoder, and use it to instantiate a flow solver
    print('instantiating encoder and solver...')
    instantiate_time = time.time()
    encoder = matcher.metadata.Encoder(metadata, config, reviewer_ids)
    flow_solver = matcher.Solver(supplies, demands, encoder.cost_matrix, encoder.constraint_matrix)
    print("took {0:.2f} seconds".format(time.time() - instantiate_time))

    print('finding solution...')
    solution_time = time.time()
    solution = flow_solver.solve()
    print("took {0:.2f} seconds".format(time.time() - solution_time))

    # decode the solution matrix
    print('decoding solution...')
    decoding_time = time.time()
    assignments_by_forum, alternates_by_forum, overflow_by_reviewer = encoder.decode(solution)
    print("took {0:.2f} seconds".format(time.time() - decoding_time))

    print('posting new config and assignments...')
    post_time = time.time()
    client.post_note(openreview.Note(**{
        'invitation': config_inv.id,
        'readers': config_inv.reply['readers']['values'],
        'writers': config_inv.reply['writers']['values'],
        'signatures': config_inv.reply['signatures']['values'],
        'content': config
    }))

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
                'alternateGroups': alternates_by_forum.get(forum, [])
            }
        }))
    print("took {0:.2f} seconds".format(time.time() - post_time))

    print('overflow by reviewer')
    print(overflow_by_reviewer)
