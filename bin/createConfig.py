import argparse
import openreview


def createConfig ():
    note = openreview.Note(invitation="ICLR.cc/2019/Conference/-/Assignment_Configuration",readers=['ICLR.cc/2019/Conference','ICLR.cc/2019/Conference/Program_Chairs'], writers=['ICLR.cc/2019/Conference'], signatures=['ICLR.cc/2019/Conference'],
                           content={
                               "label": "reviewers-1",
                               "weights": {
                                   "bid_score": 1.0,
                                   "tpms_score": 1.0
                               },
                               "max_users": 3,
                               "max_papers": 4,
                               "min_papers": 3,
                               "alternates": 5,
                               "constraints": {},
                               "config_invitation": "ICLR.cc/2019/Conference/-/Assignment_Configuration",
                               "paper_invitation": "ICLR.cc/2019/Conference/-/Blind_Submission",
                               "metadata_invitation": "ICLR.cc/2019/Conference/-/Paper_Metadata",
                               "assignment_invitation": "ICLR.cc/2019/Conference/-/Paper_Assignment",
                               "match_group": "ICLR.cc/2019/Conference/Reviewers",
                               "status": "pending"
                           })
    return note



# Some useful code for creating a config note for testing the matcher if you want to use POSTMAN and a
# POST /match request using the configNoteId of the note id produced below.  A header including an AUthorization token is also necessary
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseurl', help="openreview base URL")
    parser.add_argument('--username')
    parser.add_argument('--password')

    args = parser.parse_args()
    client = openreview.Client(baseurl=args.baseurl, username=args.username, password=args.password)
    note = createConfig()

    # note = client.get_note('frc7bUGoYF')
    note = client.post_note(note)
    # note.content['status'] = 'pending'
    # note.content['min_papers'] = 3
    # note = client.post_note(note)
    print("Note create has id:", note.id)
    print(note)
