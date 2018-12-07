import os
import csv
import logging

from website.app import setup_django
setup_django()

from osf.models import Registration
from scripts import utils

logger = logging.getLogger(__name__)


COMMENT_LIMIT_FOR_ANALYSIS = 10


def main():

    registrations_with_comments = Registration.objects.filter(comment__isnull=False).prefetch_related('guids')
    output = []
    if registrations_with_comments.count() < COMMENT_LIMIT_FOR_ANALYSIS:
        logger.info(
            'There are less than {} guids for registrations with comments, just outputting those...'.format(
                COMMENT_LIMIT_FOR_ANALYSIS
            )
        )
        for registration in registrations_with_comments:
            output.append({'guid': registration._id})
    else:
        logger.info(
            'There are {} registrations with comments, gathering more info...'.format(
                registrations_with_comments.count()
            )
        )
        # how many comments on each registration, how many levels of comments(?), and length of comments.
        # TODO - replace comments_have_replies with levels of comments if possible
        for registration in registrations_with_comments:
            output.append({
                'registration_guid': registration._id,
                'number_of_comments': registration.comment_set.count(),
                'comments_have_replies': registration.comment_set.count() > registration.comment_set.filter(target=registration.guids.first().id).count(),
                'length_of_comments': len(''.join(registration.comment_set.values_list('content', flat=True)))
            })

    if output:
        filename = os.path.join(os.path.expanduser('~'), 'registration_comment_data.csv')
        with open(filename, mode='w') as csv_file:
                fieldnames = output[0].keys()
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in output:
                    writer.writerow(row)


if __name__=='__main__':
    utils.add_file_logger(logger, __file__)

    main()
