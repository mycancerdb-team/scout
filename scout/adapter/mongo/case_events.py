import logging
from datetime import datetime

from bson import ObjectId
import pymongo

from scout.constants import CASE_STATUSES, REV_ACMG_MAP

LOG = logging.getLogger(__name__)


class CaseEventHandler(object):
    """Class to handle case events for the mongo adapter"""

    def assign(self, institute, case, user, link):
        """Assign a user to a case.

        This function will create an Event to log that a person has been assigned
        to a case. Also the user will be added to case "assignees".

        Arguments:
            institute (dict): A institute
            case (dict): A case
            user (dict): A User object
            link (str): The url to be used in the event

        Returns:
            updated_case(dict)
        """
        LOG.info(
            "Creating event for assigning {0} to {1}".format(
                user["name"].encode("utf-8"), case["display_name"]
            )
        )

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="assign",
            subject=case["display_name"],
        )
        LOG.info(
            "Updating {0} to be assigned with {1}".format(
                case["display_name"], user["name"]
            )
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$addToSet": {"assignees": user["_id"]}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return updated_case

    def unassign(self, institute, case, user, link, inactivate=False):
        """Unassign a user from a case.

        This function will create an Event to log that a person has been
        unassigned from a case. Also the user will be removed from case
        "assignees".

        Arguments:
            institute (dict): A Institute object
            case (dict): A Case object
            user (dict): A User object (Should this be a user id?)
            link (dict): The url to be used in the event
            inactivate(bool): inactivate case if there are no assignees

        Returns:
            updated_case (dict): The updated case
        """
        LOG.info(
            "Creating event for unassigning {0} from {1}".format(
                user["name"], case["display_name"]
            )
        )

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="unassign",
            subject=case["display_name"],
        )

        LOG.info(
            "Updating {0} to be unassigned with {1}".format(
                case["display_name"], user["name"]
            )
        )

        # if case is not prioritized and user wishes to inactivate it:
        if case["status"] != "prioritized" and inactivate:
            # flag case as inactive:
            case["status"] = "inactive"

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$pull": {"assignees": user["_id"]}, "$set": {"status": case["status"]}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def update_status(self, institute, case, user, status, link):
        """Update the status of a case.

        This function will create an Event to log that a user have updated the
        status of a case. Also the status of the case will be updated.
        Status could be anyone of:
            ("prioritized", "inactive", "active", "solved", "archived")

        Arguments:
            institute (dict): A Institute object
            case (dict): A Case object
            user (dict): A User object
            status (str): The new status of the case
            link (str): The url to be used in the event

        Returns:
            updated_case
        """

        if status not in CASE_STATUSES:
            LOG.warning("Status {0} is invalid".format(status))
            return None

        LOG.info(
            "Creating event for updating status of {0} to {1}".format(
                case["display_name"], status
            )
        )

        # assign case to user if user unarchives it
        if case.get("status") == "archived" and status == "active":
            LOG.info("assign case to user {}".format(user["email"]))
            self.assign(institute, case, user, link)

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="status",
            subject=case["display_name"],
        )

        LOG.info("Updating {0} to status {1}".format(case["display_name"], status))
        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"status": status}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")

        return updated_case

    def update_synopsis(self, institute, case, user, link, content=""):
        """Create an Event for updating the synopsis for a case.

            This function will create an Event and update the synopsis for
             a case.

        Arguments:
            institute (dict): A Institute object
            case (dict): A Case object
            user (dict): A User object
            link (str): The url to be used in the event
            content (str): The content for what should be added to the synopsis

        Returns:
            updated_case
        """
        LOG.info(
            "Creating event for updating the synopsis for case"
            " {0}".format(case["display_name"])
        )

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="synopsis",
            subject=case["display_name"],
            content=content,
        )

        LOG.info("Updating the synopsis for case {0}".format(case["display_name"]))
        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"synopsis": content}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def archive_case(self, institute, case, user, link):
        """Create an event for archiving a case.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event

        Returns:
            updated_case (dict)
        """
        LOG.info("Creating event for archiving case {0}".format(case["display_name"]))

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="archive",
            subject=case["display_name"],
        )

        LOG.info(
            "Change status for case {0} to 'archived'".format(case["display_name"])
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"status": "archived"}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def open_research(self, institute, case, user, link):
        """Create an event for opening the research list a case.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event

        Returns:
            updated_case(dict)
        """
        LOG.info(
            "Creating event for opening research for case"
            " {0}".format(case["display_name"])
        )

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="open_research",
            subject=case["display_name"],
        )

        LOG.info(
            "Set research_requested for case {0} to True".format(case["display_name"])
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"research_requested": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def request_rerun(self, institute, case, user, link):
        """Request a case to be re-analyzed.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event

        Return:
            updated_case
        """
        if case.get("rerun_requested"):
            raise ValueError("rerun already pending")

        if case.get("status") == "archived":
            # assign case to user requesting rerun
            self.assign(institute, case, user, link)

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="rerun",
            subject=case["display_name"],
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"rerun_requested": True}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def share(self, institute, case, collaborator_id, user, link):
        """Share a case with a new institute.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            collaborator_id (str): A instute id
            user (dict): A User object
            link (str): The url to be used in the event

        Return:
            updated_case
        """
        if collaborator_id in case.get("collaborators", []):
            raise ValueError("new customer is already a collaborator")

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="share",
            subject=collaborator_id,
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$push": {"collaborators": collaborator_id}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def unshare(self, institute, case, collaborator_id, user, link):
        """Revoke access for a collaborator for a case.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            collaborator_id (str): A instute id
            user (dict): A User object
            link (str): The url to be used in the event

        Return:
            updated_case

        """
        if collaborator_id not in case["collaborators"]:
            raise ValueError("collaborator doesn't have access to case")

        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="unshare",
            subject=collaborator_id,
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$pull": {"collaborators": collaborator_id}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def diagnose(self, institute, case, user, link, level, omim_id, remove=False):
        """Diagnose a case using OMIM ids.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event
            level (str): choices=('phenotype','gene')

        Return:
            updated_case

        """
        if level == "phenotype":
            case_key = "diagnosis_phenotypes"
        elif level == "gene":
            case_key = "diagnosis_genes"
        else:
            raise TypeError("wrong level")

        diagnosis_list = case.get(case_key, [])
        omim_number = int(omim_id.split(":")[-1])

        updated_case = None
        if remove and omim_number in diagnosis_list:
            updated_case = self.case_collection.find_one_and_update(
                {"_id": case["_id"]},
                {"$pull": {case_key: omim_number}},
                return_document=pymongo.ReturnDocument.AFTER,
            )

        elif omim_number not in diagnosis_list:
            updated_case = self.case_collection.find_one_and_update(
                {"_id": case["_id"]},
                {"$push": {case_key: omim_number}},
                return_document=pymongo.ReturnDocument.AFTER,
            )

        if updated_case:
            self.create_event(
                institute=institute,
                case=case,
                user=user,
                link=link,
                category="case",
                verb="update_diagnosis",
                subject=case["display_name"],
                content=omim_id,
            )

        return updated_case

    def add_cohort(self, institute, case, user, link, tag):
        """Add a cohort tag to case

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event
            tag (str): The cohort tag to be added

        Return:
            updated_case(dict)
        """
        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="add_cohort",
            subject=link,
        )

        LOG.info("Adding cohort tag {0} to {1}".format(tag, case["display_name"]))

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$addToSet": {"cohorts": tag}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def remove_cohort(self, institute, case, user, link, tag):
        """Remove a cohort tag from case

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event
            tag (str): The cohort tag to be removed

        Return:
            updated_case(dict)
        """
        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="remove_cohort",
            subject=case["display_name"],
        )

        LOG.info("Removing cohort tag {0} to {1}".format(tag, case["display_name"]))

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$pull": {"cohorts": tag}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def mark_checked(self, institute, case, user, link, unmark=False):
        """Mark a case as checked from an analysis point of view.

        Arguments:
            institute (dict): A Institute object
            case (dict): Case object
            user (dict): A User object
            link (str): The url to be used in the event
            unmark (bool): If case should ve unmarked

        Return:
            updated_case
        """

        LOG.info("Updating checked status of {}".format(case["display_name"]))

        status = "not checked" if unmark else "checked"
        self.create_event(
            institute=institute,
            case=case,
            user=user,
            link=link,
            category="case",
            verb="check_case",
            subject=status,
        )

        LOG.info(
            "Updating {0}'s checked status {1}".format(case["display_name"], status)
        )
        analysis_checked = False if unmark else True
        updated_case = self.case_collection.find_one_and_update(
            {"_id": case["_id"]},
            {"$set": {"analysis_checked": analysis_checked}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def update_clinical_filter_hpo(
        self, institute_obj, case_obj, user_obj, link, hpo_clinical_filter
    ):
        """Update HPO clinical filter setting for a case.

        Arguments:
            institute_obj (dict): A Institute object
            case_obj (dict): Case object
            user_obj (dict): A User object
            link (str): The url to be used in the event
            hpo_clinical_filter (bool): Toggle for use of dynamic gene panel in clinical filter.
        Return:
            updated_case(dict)
        """
        self.create_event(
            institute=institute_obj,
            case=case_obj,
            user=user_obj,
            link=link,
            category="case",
            verb="update_clinical_filter_hpo",
            subject=case_obj["display_name"],
        )

        LOG.info(
            "Update HPO clinical filter status for {}".format(case_obj["display_name"])
        )

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case_obj["_id"]},
            {"$set": {"hpo_clinical_filter": hpo_clinical_filter}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")
        return updated_case

    def update_default_panels(
        self, institute_obj, case_obj, user_obj, link, panel_objs
    ):
        """Update default panels for a case.

        Arguments:
            institute_obj (dict): A Institute object
            case_obj (dict): Case object
            user_obj (dict): A User object
            link (str): The url to be used in the event
            panel_objs (list(dict)): List of panel objs

        Return:
            updated_case(dict)

        """
        self.create_event(
            institute=institute_obj,
            case=case_obj,
            user=user_obj,
            link=link,
            category="case",
            verb="update_default_panels",
            subject=case_obj["display_name"],
        )

        LOG.info("Update default panels for {}".format(case_obj["display_name"]))

        panel_ids = [panel["_id"] for panel in panel_objs]

        for existing_panel in case_obj["panels"]:
            if existing_panel["panel_id"] in panel_ids:
                existing_panel["is_default"] = True
            else:
                existing_panel["is_default"] = False

        updated_case = self.case_collection.find_one_and_update(
            {"_id": case_obj["_id"]},
            {"$set": {"panels": case_obj["panels"]}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        LOG.debug("Case updated")

        return updated_case
