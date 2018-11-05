import openreview
from matcher import app
from matcher.solver import Solver
from matcher.encoder import Encoder

# A task that runs as a separate thread with errors logged to the app.
def match_task (config_note, client):
    try:
        app.logger.debug("Starting task to assign reviewers for configId: " + config_note.id)
        config_note = compute_match(config_note, client)
        app.logger.debug("Finished task for configId: " + config_note.id)
    except Exception as e:
        app.logger.debug("Failed to complete matching for configId: " + config_note.id)
        app.logger.error('Internal error:', exc_info=True)
    finally:
        return config_note


# A function that can be called from a script to compute a match.
# Given a config_note and an openreview.client object, this will compute a match of
# reviewers to papers and post it to the db.  It will return the config note with a status field
# set to 'complete' if it succeeds.  Otherwise a failure message will be placed in the status field.
def compute_match(config_note, client):
    try:
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
        # clear the existing assignments from previous runs of this.
        clear_existing_match(assignment_inv, client)
        # instantiate the metadata encoder, and use it to instantiate a flow solver
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

        # find a solution
        solution = flow_solver.solve()
        if flow_solver.is_solved():
            # decode the solution matrix
            assignments_by_forum, alternates_by_forum = encoder.decode(solution)
            # put the proposed assignment in the db
            save_suggested_assignment(alternates_by_forum, assignment_inv, assignments_by_forum, client, config)
            config_note.content['status'] = 'complete'
            client.post_note(config_note)
        else:
            config_note.content['status'] = 'Failure: Solver could not find a solution.  Adjust your parameters'
            client.post_note(config_note)
    # If any exception occurs while processing we need to set the status of the config note to indicate
    # failure.
    except Exception as e:
        config_note.content['status'] = 'Failure: Internal Error while running solver'
        client.post_note(config_note)
        raise e
    finally:
        return config_note


# delete assignment notes created by previous runs of matcher
def clear_existing_match(assignment_inv, client):
    # TODO don't use notes (see below)
    for assignment_note in openreview.tools.iterget_notes(client, invitation=assignment_inv.id):
        client.delete_note(assignment_note)


# save the assignment as a set of notes.
def save_suggested_assignment (alternates_by_forum, assignment_inv, assignments_by_forum, client, config):
    # post assignments
    # TODO don't use notes.  Use some other more efficient representation to store the reviewer->paper match.
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
