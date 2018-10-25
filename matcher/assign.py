import openreview
import time
import traceback
from matcher import app
from matcher.solver import Solver
from matcher.encoder import Encoder


def run_match(config_note, client):
    try:
        app.logger.debug("Starting task to assign reviewers for configId: " + config_note.id)
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

        minimums = [config['min_papers']] * len(reviewer_ids)
        maximums = [config['max_papers']] * len(reviewer_ids)



        # enter 'processing' phase
        config_note.content['status'] = 'processing'
        config_note = client.post_note(config_note)

        app.logger.info('clearing existing assignments...')
        clear_time = time.time()
        for assignment_note in openreview.tools.iterget_notes(client, invitation=assignment_inv.id):
            client.delete_note(assignment_note)
        app.logger.info('took {0:.2f} seconds'.format(time.time() - clear_time))

        # instantiate the metadata encoder, and use it to instantiate a flow solver
        app.logger.info('instantiating encoder and solver...')
        instantiate_time = time.time()
        encoder = Encoder(metadata, config, reviewer_ids)
        # The config contains custom_loads which is a dictionary where keys are user names
        # and values are max values to override the max_papers coming from the general config.
        for reviewer_id, custom_load in config.get('custom_loads',{}).items():
            if reviewer_id in encoder.index_by_reviewer:
                reviewer_index = encoder.index_by_reviewer[reviewer_id]
                maximums[reviewer_index] = custom_load
                if custom_load < minimums[reviewer_index]:
                    minimums[reviewer_index] = custom_load
        flow_solver = Solver(minimums, maximums, demands, encoder.cost_matrix, encoder.constraint_matrix)
        app.logger.info('took {0:.2f} seconds'.format(time.time() - instantiate_time))

        app.logger.info('finding solution...')
        solution_time = time.time()
        solution = flow_solver.solve()
        if flow_solver.is_solved():
            app.logger.info('took {0:.2f} seconds'.format(time.time() - solution_time))

            # decode the solution matrix
            app.logger.info('decoding solution...')
            decoding_time = time.time()
            assignments_by_forum, alternates_by_forum = encoder.decode(solution)
            app.logger.info('took {0:.2f} seconds'.format(time.time() - decoding_time))

            app.logger.info('posting assignments...')
            posting_time = time.time()
            for forum, assignments in assignments_by_forum.items():
                alternates = alternates_by_forum[forum]
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
                        'alternateGroups': alternates
                    }
                }))
            app.logger.info('took {0:.2f} seconds'.format(time.time() - posting_time))

            config_note.content['status'] = 'complete'
            client.post_note(config_note)
            app.logger.info('done. total time: {0:.2f} seconds'.format(time.time() - start_time))
            app.logger.debug("Completed task to assign reviewers for configId: " + config_note.id)
        else:
            app.logger.info('Solver could not find a solution')
            config_note.content['status'] = 'Failure: Solver could not find a solution.  Adjust your parameters'
            client.post_note(config_note)
    # If any exception occurs while processing we need to set the status of the config note to indicate
    # failure.
    except Exception as e:
        app.logger.debug("Failed to complete task to assign reviewers for configId: " + config_note.id)
        app.logger.error('Internal error:', exc_info=True)
        config_note.content['status'] = 'Failure: Internal Error while running solver'
        client.post_note(config_note)
    finally:
        return None