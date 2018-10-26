import argparse
import openreview

# A highly useful utility which builds a config note so that the matcher web app can be tested with "real" inputs (ICLR 2019 meta data)
#  One would need to use some kind of HTTP client (e.g. curl or Postman) to call the app using the note id produced by this.

def create_config (params):
    conf = params['conf_name'] + "/" + str(params['year']) + "/Conference"
    note = openreview.Note(invitation='%s/-/Assignment_Configuration' % conf,
                           readers=['%s' % conf,'%s/Program_Chairs' % conf],
                           writers=['%s' % conf], signatures=['%s' % conf],
                           content={
                               "label": params['label'],
                               "weights": {
                                   "bid_score": params['bid_weight'],
                                   "tpms_score": params['tpms_weight']
                               },
                               "max_users": params['max_users'],
                               "max_papers": params['max_papers'],
                               "min_papers": params['min_papers'],
                               "alternates": params['alternates'],
                               "constraints": {},
                               "config_invitation": "%s/-/Assignment_Configuration" % conf,
                               "paper_invitation": "%s/-/Blind_Submission" % conf,
                               "metadata_invitation": "%s/-/Paper_Metadata" % conf,
                               "assignment_invitation": "%s/-/Paper_Assignment" % conf,
                               "match_group": "%s/Reviewers" % conf,
                               "status": "pending"
                           })
    return note


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseurl', help="openreview base URL")
    parser.add_argument('--username')
    parser.add_argument('--password')

    args = parser.parse_args()
    client = openreview.Client(baseurl=args.baseurl, username=args.username, password=args.password)

    # Use the ICLR 2019 as an example of meta data
    params = {'conf_name': 'ICLR.cc', 'label': 'reviewers-1', 'bid_weight': 1.0, 'tpms_weight': 1.0, 'year': 2019,
              'max_users': 3, 'max_papers': 4, 'min_papers': 3, 'alternates': 5}
    note = create_config(params)
    note = client.post_note(note)
    print("Created config note:", note.id)
    print(note)
