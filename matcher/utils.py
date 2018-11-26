#!/usr/bin/python
# -*- coding: utf-8 -*-
import openreview
from functools import reduce


# sums list of numbers and omits things like 'inf' and '-inf'
def safe_sum(lst):
    sum = 0
    for n in lst:
        if type(n) == float:
            sum += n
    return sum


def weight_scores(scores, weights):
    '''
    scores: a dict of scores keyed on score name

    weights: a dict of weights keyed on score name

    returns a dict of weighted scores, keyed on score names found in @weights
    (i.e. result ignores values in @scores that are not present in @weights)

    Example:

    >>> weight_scores({'tpms': 0.5, 'bid': 1.0 }, { 'tpms': 1.5 })
    {'tpms': 0.75}

    '''
    weighted_scores = {}
    for feature in weights:
        if feature in scores:
            weighted_scores[feature] = scores[feature] * weights[feature]

    return weighted_scores


def cost(scores, weights, precision=0.01):
    weighted_scores = weight_scores(scores, weights)
    score_sum = safe_sum(weighted_scores.values())
    return -1 * int(score_sum / precision)


def get_conflicts(author_profiles, user_profile):
    author_domains = set()
    author_emails = set()
    author_relations = set()

    for author_email, profile in author_profiles.items():
        author_info = get_author_info(profile, author_email)

        author_domains.update(author_info['domains'])
        author_emails.update(author_info['emails'])
        author_relations.update(author_info['relations'])

    user_info = get_profile_info(user_profile)

    conflicts = set()
    conflicts.update(author_domains.intersection(user_info['domains']))
    conflicts.update(author_relations.intersection(user_info['emails']))
    conflicts.update(author_emails.intersection(user_info['relations']))
    conflicts.update(author_emails.intersection(user_info['emails']))

    return list(conflicts)


def get_author_info(profile, email):
    if profile:
        return get_profile_info(profile)
    else:
        return {
            'domains': openreview.tools.subdomains(email),
            'emails': [email],
            'relations': []
        }


def get_profile_info(profile):
    domains = set()
    emails = set()
    relations = set()

    ## Emails section
    for email in profile.content['emails']:
        domains.update(openreview.tools.subdomains(email))
        emails.add(email)

    ## Institution section
    for h in profile.content.get('history', []):
        domain = h.get('institution', {}).get('domain', '')
        domains.update(openreview.tools.subdomains(domain))

    ## Relations section
    relations.update([r['email'] for r in profile.content.get('relations', [])])

    ## Filter common domains
    if 'gmail.com' in domains:
        domains.remove('gmail.com')

    return {
        'domains': domains,
        'emails': emails,
        'relations': relations
    }
