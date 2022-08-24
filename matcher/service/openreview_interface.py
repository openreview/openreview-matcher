import re
import openreview
import logging
from tqdm import tqdm
from matcher.encoder import EncoderError
from matcher.core import MatcherError, MatcherStatus
from openreview.api import Note


class ConfigNoteInterface:
    def __init__(
        self,
        client,
        client_v2,
        config_note_id,
        logger=logging.getLogger(__name__),
    ):
        self.client = client
        self.client_v2 = client_v2
        self.logger = logger
        self.logger.debug("GET note id={}".format(config_note_id))
        try:
            config_note = self.client.get_note(config_note_id)
            self.api_version = 1
        except:
            config_note = self.client_v2.get_note(config_note_id)
            self.api_version = 2

        self.config_note = self._content_to_api1(config_note)
        self.venue_id = self.config_note.signatures[0]
        self.label = self.config_note.content["title"]
        self.match_group = self.config_note.content["match_group"]

        self.logger.debug(
            "GET invitation id={}".format(
                self.config_note.content["assignment_invitation"]
            )
        )
        if self.api_version == 1:
            self.assignment_invitation = self.client.get_invitation(
                self.config_note.content["assignment_invitation"]
            )
        elif self.api_version == 2:
            self.assignment_invitation = self.client_v2.get_invitation(
                self.config_note.content["assignment_invitation"]
            )

        self.logger.debug(
            "API version={}".format(
                self.api_version
            )
        )

        self.logger.debug(
            "GET invitation id={}".format(
                self.config_note.content["aggregate_score_invitation"]
            )
        )
        if self.api_version == 1:
            self.aggregate_score_invitation = self.client.get_invitation(
                self.config_note.content["aggregate_score_invitation"]
            )
        elif self.api_version == 2:
            self.aggregate_score_invitation = self.client_v2.get_invitation(
                self.config_note.content["aggregate_score_invitation"]
            )

        self.num_alternates = int(self.config_note.content["alternates"])
        self.paper_numbers = {}
        self.allow_zero_score_assignments = (
            self.config_note.content.get("allow_zero_score_assignments", "No")
            == "Yes"
        )
        self.probability_limits = float(
            self.config_note.content.get("randomized_probability_limits", 1.0)
        )

        # Lazy variables
        self._reviewers = None
        self._papers = None
        self._scores_by_type = {}
        self._minimums = None
        self._maximums = None
        self._demands = None
        self._constraints = None

        self.validate_score_spec()

    def validate_score_spec(self):
        for invitation_id in self.config_note.content.get(
            "scores_specification", {}
        ):
            try:
                if self.api_version == 1:
                    self.logger.debug("GET invitation id={}".format(invitation_id))
                    self.client.get_invitation(invitation_id)
                elif self.api_version == 2:
                    self.logger.debug("GET invitation id={}".format(invitation_id))
                    self.client_v2.get_invitation(invitation_id)
            except Exception as error_handle:
                self.set_status(MatcherStatus.ERROR, message=str(error_handle))
                raise error_handle

    def validate_group(self, group_id):
        try:
            self.logger.debug("GET group id={}".format(group_id))
            group = self.client.get_group(group_id)
            group = openreview.tools.replace_members_with_ids(
                self.client, group
            )
            for member in group.members:
                if not member.startswith("~"):
                    raise openreview.OpenReviewException(
                        "All members of the group, {group}, must have an OpenReview Profile".format(
                            group=group_id
                        )
                    )
        except openreview.OpenReviewException as error_handle:
            self.set_status(MatcherStatus.ERROR, message=str(error_handle))
            raise error_handle

    @property
    def normalization_types(self):
        scores_specification = self.config_note.content.get(
            "scores_specification", {}
        )
        normalization_types = [
            invitation
            for invitation, spec in scores_specification.items()
            if spec.get("normalize", False)
        ]
        return normalization_types

    @property
    def reviewers(self):
        if self._reviewers is None:
            self.logger.debug("GET group id={}".format(self.match_group))
            match_group = self.client.get_group(self.match_group)
            self._reviewers = match_group.members
        return self._reviewers

    @property
    def papers(self):
        if self._papers is None:
            content_dict = {}
            paper_invitation = self.config_note.content["paper_invitation"]
            self.logger.debug(
                "Getting notes for invitation: {}".format(paper_invitation)
            )
            if "&" in paper_invitation:
                elements = paper_invitation.split("&")
                paper_invitation = elements[0]
                for element in elements[1:]:
                    if element:
                        if element.startswith("content.") and "=" in element:
                            key, value = element.split(".")[1].split("=")
                            content_dict[key] = value
                        else:
                            self.logger.debug(
                                'Invalid filter provided in invitation: {}. Supported filter format "content.field_x=value1".'.format(
                                    element
                                )
                            )
            if "/-/" in paper_invitation:
                if self.api_version == 1:
                    paper_notes = list(
                        openreview.tools.iterget_notes(
                            self.client,
                            invitation=paper_invitation,
                            content=content_dict,
                        )
                    )
                elif self.api_version == 2:
                    paper_notes = list(
                        openreview.tools.iterget_notes(
                            self.client_v2,
                            invitation=paper_invitation,
                            content=content_dict,
                        )
                    )

                paper_notes = [self._content_to_api1(n) for n in paper_notes]
                self._papers = [n.id for n in paper_notes]
                self.paper_numbers = {n.id: n.number for n in paper_notes}
                self.logger.debug(
                    "Count of notes found: {}".format(len(self._papers))
                )
            else:
                self.validate_group(paper_invitation)
                group = self.client.get_group(paper_invitation)
                self._papers = group.members
                self.paper_numbers = {n: 1 for n in group.members}

        return self._papers

    @property
    def minimums(self):
        if self._minimums is None:
            minimums, maximums = self._get_quota_arrays()
            self._minimums = minimums
            self._maximums = maximums

        return self._minimums

    @property
    def maximums(self):
        if self._maximums is None:
            minimums, maximums = self._get_quota_arrays()
            self._minimums = minimums
            self._maximums = maximums

        return self._maximums

    def _content_to_api1(self, note):
        new_content = {}
        for key, val in note.content.items():
            if isinstance(val, dict) and 'value' in val.keys():
                new_content[key] = val['value']
            else:
                new_content[key] = val
        note.content = new_content
        return note

    def _content_to_api2(self, note):
        new_content = {}
        for key, val in note.content.items():
            if not (isinstance(val, dict) and 'value' in val.keys()):
                new_content[key] = {'value': val}
            else:
                new_content[key] = val
        note.content = new_content
        return note

    def _get_custom_demand_edges(self):
        """Helper function to get all the custom demand edges"""
        custom_demand_edges = []
        custom_demand_invitation = self.config_note.content.get(
            "custom_user_demand_invitation"
        )
        if custom_demand_invitation:
            self.logger.debug(
                "GET grouped edges invitation id={}".format(
                    custom_demand_invitation
                )
            )

            if self.api_version == 1:
                custom_demand_edges = self.client.get_grouped_edges(
                    invitation=custom_demand_invitation,
                    groupby="tail",
                    tail=self.match_group,
                    select="head,weight",
                )
            elif self.api_version == 2:
                custom_demand_edges = self.client_v2.get_grouped_edges(
                    invitation=custom_demand_invitation,
                    groupby="tail",
                    tail=self.match_group,
                    select="head,weight",
                )

        return custom_demand_edges

    def _get_custom_supply_edges(self):
        """Helper function to get all the custom supply edges"""
        custom_supply_edges = []
        custom_supply_invitation = self.config_note.content.get(
            "custom_max_papers_invitation"
        )
        if custom_supply_invitation:
            self.logger.debug(
                "GET grouped edges invitation id={}".format(
                    custom_supply_invitation
                )
            )

            if self.api_version == 1:
                custom_supply_edges = self.client.get_grouped_edges(
                    invitation=custom_supply_invitation,
                    groupby="head",
                    head=self.match_group,
                    select="tail,weight",
                )
            elif self.api_version == 2:
                custom_supply_edges = self.client_v2.get_grouped_edges(
                    invitation=custom_supply_invitation,
                    groupby="head",
                    head=self.match_group,
                    select="tail,weight",
                )

        return custom_supply_edges

    @property
    def demands(self):
        if self._demands is None:
            user_demand_value = (
                self.config_note.content.get("user_demand")
                if "user_demand" in self.config_note.content
                else self.config_note.content["max_users"]
            )
            self._demands = [int(user_demand_value) for paper in self.papers]
            custom_demand_edges = self._get_custom_demand_edges()
            count_processed_edges = 0
            if custom_demand_edges:
                map_papers_to_idx = {
                    p: idx for idx, p in enumerate(self.papers)
                }
                for edge in custom_demand_edges[0]["values"]:
                    idx = map_papers_to_idx.get(edge["head"], -1)
                    if idx >= 0:
                        self._demands[idx] = int(edge["weight"])
                        count_processed_edges += 1
                self.logger.debug(
                    "Custom demands recorded for {} papers".format(
                        count_processed_edges
                    )
                )
            self.logger.debug(
                "Total demands recorded for {} papers".format(
                    len(self._demands)
                )
            )
        return self._demands

    @property
    def constraints(self):
        if self._constraints is None:
            self._constraints = [
                (edge["head"], edge["tail"], edge["weight"])
                for edge in self._get_all_edges(
                    self.config_note.content["conflicts_invitation"]
                )
            ]
        return self._constraints

    @property
    def scores_by_type(self):
        scores_specification = self.config_note.content.get(
            "scores_specification", {}
        )

        if not self._scores_by_type and scores_specification:
            edges_by_invitation = {}
            defaults_by_invitation = {}
            for invitation_id, spec in scores_specification.items():
                edges_by_invitation[invitation_id] = self._get_all_edges(
                    invitation_id
                )
                defaults_by_invitation[invitation_id] = spec.get("default", 0)

            translate_maps = {
                inv_id: score_spec["translate_map"]
                for inv_id, score_spec in scores_specification.items()
                if "translate_map" in score_spec
            }

            for inv_id, edges in edges_by_invitation.items():
                invitation_edges = [
                    (
                        edge["head"],
                        edge["tail"],
                        self._edge_to_score(
                            edge, translate_map=translate_maps.get(inv_id)
                        ),
                    )
                    for edge in edges
                ]
                self._scores_by_type[inv_id] = {
                    "default": defaults_by_invitation[inv_id],
                    "edges": invitation_edges,
                }
        return self._scores_by_type

    @property
    def weight_by_type(self):
        scores_specification = self.config_note.content.get(
            "scores_specification", {}
        )
        weight_by_type = {}
        if scores_specification:
            weight_by_type = {
                inv_id: entry["weight"]
                for inv_id, entry in scores_specification.items()
            }
        return weight_by_type

    def set_status(self, status, message="", additional_status_info={}):
        """Set the status of the config note"""

        # Catch none message
        if message is None:
            message = ''

        self.config_note.content["status"] = status.value
        self.config_note.content["error_message"] = message
        for key, value in additional_status_info.items():
            print("Save property", key, value)
            self.config_note.content[key] = value

        if self.api_version == 1:
            self.config_note = self.client.post_note(self.config_note)
        elif self.api_version == 2:
            config_note_v2 = self.client_v2.post_note_edit(
                invitation="{}/-/Assignment_Configuration".format(self.match_group),
                signatures=[self.venue_id],
                note=Note(id=self.config_note.id, content=self._content_to_api2(self.config_note).content)
            )
            self.config_note = self._content_to_api1(self.client_v2.get_note(self.config_note.id))

        self.logger.debug(
            "Config Note {} status set to: {}".format(
                self.config_note.id, self.config_note.content["status"]
            )
        )

    def set_assignments(self, assignments_by_forum):
        """Helper function for posting assignments returned by the Encoder"""

        self.logger.debug(
            "saving {} edges".format(self.assignment_invitation.id)
        )

        assignment_edges = []
        score_edges = []

        for forum, assignments in assignments_by_forum.items():
            paper_number = self.paper_numbers[forum]
            for paper_user_entry in assignments:
                score = paper_user_entry["aggregate_score"]
                user = paper_user_entry["user"]

                assignment_edges.append(
                    self._build_edge(
                        self.assignment_invitation,
                        forum,
                        user,
                        score,
                        self.label,
                        paper_number,
                    )
                )

                score_edges.append(
                    self._build_edge(
                        self.aggregate_score_invitation,
                        forum,
                        user,
                        score,
                        self.label,
                        paper_number,
                    )
                )

        # Find the API1/2 invitation
        if self.api_version == 1:
            self.client.get_invitation(self.assignment_invitation.id)
            openreview.tools.post_bulk_edges(self.client, assignment_edges)
            openreview.tools.post_bulk_edges(self.client, score_edges)
        elif self.api_version == 2:
            self.client_v2.get_invitation(self.assignment_invitation.id)
            openreview.tools.post_bulk_edges(self.client_v2, assignment_edges)
            openreview.tools.post_bulk_edges(self.client_v2, score_edges)

        self.logger.debug(
            "posted {} assignment edges".format(len(assignment_edges))
        )
        self.logger.debug(
            "posted {} aggregate score edges".format(len(score_edges))
        )

    def set_alternates(self, alternates_by_forum):
        """Helper function for posting alternates returned by the Encoder"""

        score_edges = []
        for forum, assignments in alternates_by_forum.items():
            paper_number = self.paper_numbers[forum]

            for paper_user_entry in assignments:
                score = paper_user_entry["aggregate_score"]
                user = paper_user_entry["user"]

                score_edges.append(
                    self._build_edge(
                        self.aggregate_score_invitation,
                        forum,
                        user,
                        score,
                        self.label,
                        paper_number,
                    )
                )
        if self.api_version == 1:
            openreview.tools.post_bulk_edges(self.client, score_edges)
        elif self.api_version == 2:
            openreview.tools.post_bulk_edges(self.client_v2, score_edges)

        self.logger.debug(
            "posted {} aggregate score edges for alternates".format(
                len(score_edges)
            )
        )

    def _get_quota_arrays(self):
        """get `minimum` and `maximum` reviewer load arrays, accounting for custom loads"""
        minimums = [
            int(self.config_note.content["min_papers"]) for r in self.reviewers
        ]
        maximums = [
            int(self.config_note.content["max_papers"]) for r in self.reviewers
        ]

        custom_supply_edges = self._get_custom_supply_edges()
        if custom_supply_edges:
            map_reviewers_to_idx = {
                r: idx for idx, r in enumerate(self.reviewers)
            }

            count_processed_edges = 0
            for edge in custom_supply_edges[0].get("values"):
                reviewer = edge["tail"]
                index = map_reviewers_to_idx.get(reviewer, -1)
                if index >= 0:
                    load = int(edge["weight"])
                    maximums[index] = min(
                        maximums[index], load if load > 0 else 0
                    )
                    minimums[index] = min(minimums[index], maximums[index])
                    count_processed_edges += 1
            self.logger.debug(
                "Custom supply recorded for {} users".format(
                    count_processed_edges
                )
            )

        return minimums, maximums

    def _get_all_edges(self, edge_invitation_id):
        """Helper function for retrieving and parsing all edges in bulk"""

        all_edges = []
        all_papers = {p: p for p in self.papers}
        all_reviewers = {r: r for r in self.reviewers}
        self.logger.debug("GET invitation id={}".format(edge_invitation_id))

        if self.api_version == 1:
            edges_grouped_by_paper = self.client.get_grouped_edges(
                invitation=edge_invitation_id,
                groupby="head",
                select="tail,label,weight",
            )
        elif self.api_version == 2:
            edges_grouped_by_paper = self.client_v2.get_grouped_edges(
                invitation=edge_invitation_id,
                groupby="head",
                select="tail,label,weight",
            )

        self.logger.debug(
            "GET grouped edges invitation id={}".format(edge_invitation_id)
        )
        filtered_edges_groups = list(
            filter(
                lambda edge_group: edge_group["id"]["head"] in all_papers,
                edges_grouped_by_paper,
            )
        )

        for group in filtered_edges_groups:
            forum_id = group["id"]["head"]
            filtered_edges = list(
                filter(
                    lambda group_value: group_value["tail"] in all_reviewers,
                    group["values"],
                )
            )
            for edge in filtered_edges:
                all_edges.append(
                    {
                        "invitation": edge_invitation_id,
                        "head": forum_id,
                        "tail": edge["tail"],
                        "weight": edge.get("weight"),
                        "label": edge.get("label"),
                    }
                )
        return all_edges

    def _build_edge(
        self, invitation, forum_id, reviewer, score, label, number
    ):
        """
        Helper function for constructing an openreview.Edge object.
        Readers, nonreaders, writers, and signatures are automatically filled based on the invitaiton.
        """
        if self.api_version == 1:
            return openreview.Edge(
                head=forum_id,
                tail=reviewer,
                weight=score,
                label=label,
                invitation=invitation.id,
                readers=self._get_values(
                    invitation, number, "readers", forum_id, reviewer
                ),
                nonreaders=self._get_values(invitation, number, "nonreaders"),
                writers=self._get_values(invitation, number, "writers"),
                signatures=[self.venue_id],
            )
        elif self.api_version == 2:
            return openreview.api.Edge(
                head=forum_id,
                tail=reviewer,
                weight=score,
                label=label,
                invitation=invitation.id,
                readers=self._get_values(
                    invitation, number, "readers", forum_id, reviewer
                ),
                nonreaders=self._get_values(invitation, number, "nonreaders"),
                writers=self._get_values(invitation, number, "writers"),
                signatures=[self.venue_id],
            )

    def _get_values(self, invitation, number, property, head=None, tail=None):
        """Return values compatible with the field `property` in invitation.reply.content"""
        values = []

        # Perform API2 check
        if getattr(invitation, "reply", None) is not None:
            property_params = invitation.reply.get(property, {})
        elif getattr(invitation, "edit", None) is not None:
            property_params = invitation.edit.get(property, {})
        else:
            raise openreview.OpenReviewException('Reply/Edge attribute not present in invitation')

        parsed_params = []
        if isinstance(property_params, list):
            for param in property_params:
                if '$' not in param:
                    parsed_params.append(param)
                else:
                    new_param = param.replace("${{2/head}/number}", str(number))
                    if head:
                        new_param = new_param.replace("${2/tail}", tail)
                    if tail:
                        new_param = new_param.replace("${2/head}", head)
                    parsed_params.append(new_param)
            return parsed_params


        if "values" in property_params:
            values = property_params.get("values", [])
        elif "values-regex" in property_params:
            regex_pattern = property_params["values-regex"]
            values = []

            for group_id in regex_pattern.split("|"):
                group_id = group_id.replace("^", "").replace("$", "")
                if "Paper.*" in group_id:
                    group_id = group_id.replace(
                        "Paper.*", "Paper{}".format(number)
                    )
                    values.append(group_id)
        elif "values-copied" in property_params:
            values_copied = property_params["values-copied"]

            for value in values_copied:
                if value == "{tail}":
                    values.append(tail)
                elif value == "{head}":
                    values.append(head)
                else:
                    values.append(value)

        return [v.replace("{head.number}", str(number)) for v in values]

    def _edge_to_score(self, edge, translate_map=None):
        """
        Given an openreview.Edge, and a mapping defined by `translate_map`,
        return a numeric score, given an Edge.
        """

        score = edge["weight"]

        if translate_map:
            try:
                score = translate_map[edge["label"]]
            except KeyError:
                raise EncoderError(
                    "Cannot translate label {} to score. Valid labels are: {}".format(
                        edge["label"], translate_map.keys()
                    )
                )

        if not isinstance(score, float) and not isinstance(score, int):
            try:
                score = float(score)
            except ValueError:
                raise EncoderError(
                    "Edge has weight that is neither float nor int: {}, type {}".format(
                        edge["weight"], type(edge["weight"])
                    )
                )

        return score


class Deployment:
    def __init__(
        self, config_note_interface, logger=logging.getLogger(__name__)
    ):

        self.config_note_interface = config_note_interface
        self.logger = logger

    def run(self):

        try:
            self.config_note_interface.set_status(MatcherStatus.DEPLOYING)

            if self.config_note_interface.api_version == 1:
                notes = self.config_note_interface.client.get_notes(
                    invitation="OpenReview.net/Support/-/Request_Form",
                    content={"venue_id": self.config_note_interface.venue_id},
                )

                conference = openreview.helpers.get_conference(
                    self.config_note_interface.client, notes[0].id
                )

                # impersonate user to get all the permissions to deploy the groups
                conference.client.impersonate(self.config_note_interface.venue_id)
                conference.set_assignments(
                    assignment_title=self.config_note_interface.label,
                    committee_id=self.config_note_interface.match_group,
                    overwrite=True,
                    enable_reviewer_reassignment=True,
                )

                self.config_note_interface.set_status(MatcherStatus.DEPLOYED)
            elif self.config_note_interface.api_version == 2:
                notes = self.config_note_interface.client_v2.get_notes(
                    invitation="OpenReview.net/Support/-/Request_Form",
                    content={"venue_id": self.config_note_interface.venue_id},
                )

                venue = openreview.helpers.get_conference(
                    self.config_note_interface.client_v2, notes[0].id
                )

                # impersonate user to get all the permissions to deploy the groups
                venue.client.impersonate(self.config_note_interface.venue_id)
                venue.set_assignments(
                    assignment_title=self.config_note_interface.label,
                    committee_id=self.config_note_interface.match_group,
                    overwrite=True,
                    enable_reviewer_reassignment=True,
                )

                self.config_note_interface.set_status(MatcherStatus.DEPLOYED)
            if not notes:
                raise openreview.OpenReviewException("Venue request not found")

        except Exception as e:
            self.logger.error(str(e))
            self.config_note_interface.set_status(
                MatcherStatus.DEPLOYMENT_ERROR, str(e)
            )
