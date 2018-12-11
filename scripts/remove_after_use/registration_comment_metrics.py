import os
import csv
import logging

from django.db.models import Avg, Sum
from django.db.models.functions import Length

from website.app import setup_django
setup_django()

from website.settings import NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST
from osf.models import Registration
from scripts import utils

logger = logging.getLogger(__name__)


COMMENT_LIMIT_FOR_ANALYSIS = 10
HERE = os.path.dirname(os.path.abspath(__file__))


def get_comment_level(comment, depth=1):
    if type(comment.target.referent) == type(comment):
        depth += 1
        return get_comment_level(comment.target.referent, depth)
    else:
        return depth


def main():

    registrations_with_comments = Registration.objects.filter(
        comment__isnull=False
    ).exclude(
        creator__guids___id__in=NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST,
    ).prefetch_related('guids').include(None).distinct()

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
        for registration in registrations_with_comments:

            lengths = registration.comment_set.annotate(length=Length('content'))
            registration.comment_set.annotate(length=Length('content')).aggregate(Avg('length'))

            deepest_level = 1
            # iterate thru all the non-top level comments to find the deepest one
            for comment in registration.comment_set.exclude(target=registration.guids.first().id):
                comment_level = get_comment_level(comment)
                if comment_level > deepest_level:
                    deepest_level = comment_level

            comment_aggs = registration.comment_set.annotate(length=Length('content')).aggregate(sum=Sum('length'), avg=Avg('length'))
            output.append({
                'registration_guid': registration._id,
                'is_public': registration.is_public,
                'is_withdrawn': registration.is_retracted,
                'number_of_comments': registration.comment_set.count(),
                'comment_depth': deepest_level,
                'total_length_of_comments': comment_aggs['sum'],
                'average_length_of_comments': comment_aggs['avg']
            })

    if output:
        filename = os.path.join(HERE, 'registration_comment_data.csv')
        with open(filename, mode='w') as csv_file:
                fieldnames = output[0].keys()
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in output:
                    writer.writerow(row)


if __name__=='__main__':
    utils.add_file_logger(logger, __file__)

    main()
