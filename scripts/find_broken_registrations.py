# -*- coding: utf-8 -*-

# Notes!
# Nodes that are stuck in registration

# 1) Are there any logs on the original project after stuck registration?
# 2) Does the project have any add ons?
# 3) Any registrations that succeeded after the stuck registration?


import csv
from datetime import datetime

from modularodm import Q

from website.app import init_app
from website.project.model import Node
from website.archiver.model import ArchiveJob
from website.archiver import ARCHIVER_INITIATED
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA, ADDONS_REQUESTED

import logging
logger = logging.getLogger(__name__)


def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    jobs = ArchiveJob.find(
        Q('sent', 'eq', False) &
        Q('datetime_initiated', 'lt', expired_if_before) &
        Q('status', 'eq', ARCHIVER_INITIATED)
    )
    return {node.root for node in [job.dst_node for job in jobs] if node}


def analyze_failed_registration_nodes():
    """ If we can just retry the archive, but we can only do that if the
    ORIGINAL node hasn't changed.
    """
    # Get the registrations that are messed up
    failed_registration_nodes = find_failed_registrations()

    # Build up a list of dictionaries with info about these failed nodes
    failed_registration_info = []
    for broken_registration in failed_registration_nodes:
        node_logs_after_date = [
            log for log in broken_registration.registered_from.logs if log.date > broken_registration.registered_date
        ]

        # Does it have any addons?
        addon_list = [addon for addon in ADDONS_REQUESTED if broken_registration.registered_from.has_addon(addon)]
        has_addons = True if len(addon_list) > 0 else False

        # Any registrations succeeded after the stuck one?
        # Not sure why broken_registration.registered_from.registrations was always 0 locally...
        succeeded_registrations_after_failed = []
        for other_reg in Node.find(
            Q('is_registration', 'eq', True) & Q('registered_from', 'eq', broken_registration.registered_from_id)
        ):
            if other_reg.registration_approval.is_approved and other_reg.registered_date > broken_registration.registered_date:
                succeeded_registrations_after_failed.append(other_reg._id)

        can_be_reset = True if len(node_logs_after_date) == 0 and not has_addons and len(succeeded_registrations_after_failed) == 0 else False

        failed_registration_info.append(
            {
                'broken_registration_node': broken_registration._id,
                'original_node': broken_registration.registered_from_id,
                'logs_on_original_after_registration_date': node_logs_after_date,
                'has_addons': has_addons,
                'addon_list': addon_list,
                'succeeded_registrations_after_failed': succeeded_registrations_after_failed,
                'can_be_reset': can_be_reset
            }
        )

    return failed_registration_info


def save_failed_registration_info_to_csv(failed_registration_info):
    keys = failed_registration_info[0].keys()
    # Save the analysis file somewhere... here?
    with open('../../failed_registrations.csv', 'wb') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(failed_registration_info)


def main():
    init_app(routes=False)

    broken_registrations = find_failed_registrations()
    save_failed_registration_info_to_csv(broken_registrations)

    logger.info('{n} broken registrations found'.format(n=len(broken_registrations)))
    logger.info('Finished.')


if __name__ == '__main__':
    main()