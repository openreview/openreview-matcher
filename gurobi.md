## Instructions to run the Gurobi solver in the OpenReview instance

1. ssh the instance. Ask the team for the current ip address.
2. `sudo su openreview`
3. `conda activate matcher`
4. create a folder under the directory /home/openreview, `mkdir /home/openreview/gurobi_test`
5. download the data from the OpenReview API and store it in different files:
    1. `cd /home/openreview/tools`
    2. `python create_aggregate_scores.py --username your_username --password your_password --output_dir /home/openreview/gurobi_test`

      This step downloads the Affinity_Score and Bid edges and it will aggregate them, transforming the bids to a number first. If you want to change the bid invitation name or the translation map you can edit the script file.

    4. `python create_conflict_scores.py --username your_username --password your_password --output_dir /home/openreview/gurobi_test` 
    
      This step will download the conflict edges and store them in a CSV file.
      
    5. `python create_constraints.py --username your_username --password your_password --output_dir /home/openreview/gurobi_test`

      This step will download the Domain and Publications edges and create the constraint file, if you want to disable one of the constraints you should edit this file. The file contains a threshold variable to decide when the reviewer is senior or not, the current value is 12. 
      
    6. `python create_custom_max_papers.py --username your_username --password your_password --output_dir /home/openreview/gurobi_test`

      This step will download the custom quotas if they exists and download them into a file. 
      
      
 6. After all the files are downloaded, you can run the paper matching. `cd /home/openreview/gurobi_test`
 7. Run the matcher: `python -m matcher --weights 1 --scores neurips_all_scores.csv --min_papers_default 0 --max_papers_default 6 --num_reviewers 4 --num_alternates 10 --solver FairIR --constraints neurips_conflicts.csv --max_papers neurips_custom_max_papers.csv --attribute_constraints neurips_attrs.json`
 8. We recommend to use the `screen` command to run the the previous comment. To check the progress of the matching, you can check the logs in `tail -f /home/openreview/gurobi_test/default.log`
 9. Once the matching is complete, the folder will have two new files, `assignments.json` and `alternates.json` and you can upload them to the OpenReview database.
 10. `cd /home/openreview/tools`
 11. `python post_proposed_assignments.py --username your_username --password your_password --assignments_file /home/openreview/gurobi_test/assignments.json --label gurobi-test --alternates_file /home/openreview/gurobi_test/alternates.json`

      Make sure the label argument is not repeated across the multiple matcher results, that is the way to identify each different run. The output will print a url that you can use to visualize the results but you can also go to the Assignment page and check the different configurations there. One should appear with that label.
      
      
 The instance is large enough and multiple matchers can be run in parallel, make sure you use different folders for each match. You can edit the python files to modify the aggregate scores or constraints at your preference, you can also change the command line parameter: num_reviewers, min_papers_default, max_papers_default, etc. 
 
 ### How to verify the results are satisfying the domain and seniority constraints? 
 
1. Load the assignments, make sure you use the same `label` parameter

```
assignments = { e['id']['head']: [v['tail'] for v in e['values']] for e in client.get_grouped_edges(invitation='NeurIPS.cc/2023/Conference/Reviewers/-/Proposed_Assignment', label='gurobi-test', groupby='head', select='tail')}
``` 

2. Load the domain edges

```
domains = { e['id']['tail']: [v['label'] for v in e['values']][0] for e in client.get_grouped_edges(invitation='NeurIPS.cc/2023/Conference/Reviewers/-/Domain', groupby='tail', select='label')}
```

3. Load the publication count edges

```
publications = { e['id']['tail']: [v['weight'] for v in e['values']][0] for e in client.get_grouped_edges(invitation='NeurIPS.cc/2023/Conference/Reviewers/-/Publications', groupby='tail', select='weight')}
```

4. Check the constraints:

```
seniority_treshold = 12
senior_assignments = []
different_domain_assignments = []
for paper, reviewers in assignments.items():
    max_publications = max([publications.get(r, 0) for r in reviewers])
    if max_publications >= seniority_treshold:
        senior_assignments.append(paper)
    else:
        print("No seniority", paper, max_publications)

    domains_reviewers = [domains.get(r) for r in reviewers]
    if len(set(domains_reviewers)) == len(domains_reviewers):
        different_domain_assignments.append(paper)
    else:
        print("Duplicate domains", domains_reviewers)
        
len(senior_assignments)
len(assignments)
len(different_domain_assignments)
```
