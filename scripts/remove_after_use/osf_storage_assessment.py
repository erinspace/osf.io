"""
Script to generate CSV to evaulate OSF Storage usage.

"""
import io
import sys
import os
import csv
import logging
import gzip
import progressbar
from dateutil.relativedelta import relativedelta

from website.app import setup_django
setup_django()

from django.db.models import Sum
from django.utils import timezone
from django.core.paginator import Paginator

from scripts import utils
from addons.osfstorage.models import OsfStorageFile
from osf.models import FileVersion, PreprintService, Registration

logger = logging.getLogger(__name__)


EXPORT_PATH = os.path.expanduser('~')
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_SIZE = 100


def do_evaulation():
    """ This uses the last_touched datetime field, which isn't the same as last seen, but at least
    is reliably on all files!
    """
    now = timezone.now()
    keys = ['months_ago', 'number_of_files', 'total_file_size']

    file_csv = io.BytesIO()
    writer = csv.DictWriter(file_csv, fieldnames=keys)
    writer.writeheader()

    for month in range(12):
        start_date = now - relativedelta(months=month)
        end_date = now - relativedelta(months=month+1)

        files_accessed_in_range = OsfStorageFile.objects.filter(last_touched__lte=start_date, last_touched__gt=end_date).annotate(
            Sum('versions__size'),
        ).values_list(
            'versions__size__sum', flat=True
        )
        number_of_files = files_accessed_in_range.count()
        logger.info('start_date: {} end_date: {}, number_of_files: {}'.format(start_date.isoformat(), end_date.isoformat(), number_of_files))
        month_data = {
            'months_ago': month + 1,
            'number_of_files': number_of_files,
            'total_file_size': files_accessed_in_range.aggregate(sum=Sum('versions__size__sum'))['sum'] or 0
        }
        writer.writerow(month_data)

    return file_csv


def generate_raw_csv():

    keys = [
        'file_guid',
        'file_size',
        'file_version_size_sum',  #(sum of all the versions' sizes)
        'file_last_seen',
        'node_guid',
        'node_type',  #  (e.g. "osf.node", "osf.registration", "osf.quickfiles")
        'node_is_fork',
        'node_is_public',
        'node_is_deleted',
    ]

    file_csv = io.BytesIO()
    writer = csv.DictWriter(file_csv, fieldnames=keys)
    writer.writeheader()

    osf_storage_files = OsfStorageFile.objects.all().order_by('id').prefetch_related('versions', 'guids').annotate(total_file_size=Sum('versions__size'))

    logger.info('Collecting data on {} OsfStorageFiles!'.format(osf_storage_files.count()))

    progress_bar = progressbar.ProgressBar(maxval=osf_storage_files.count()).start()
    added = 0

    paginator = Paginator(osf_storage_files, PAGE_SIZE)

    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for osf_storage_file in page:
            added += 1
            first_version_size = osf_storage_file.versions.all().order_by('-created').values_list('size', flat=True).first()
            target = osf_storage_file.target
            is_deleted = getattr(target, 'is_deleted', False) or getattr(target, 'is_retracted', False) or not getattr(target, 'is_published', True)
            writer.writerow(
                {
                    'file_guid': osf_storage_file.guids.first()._id if osf_storage_file.guids.exists() else None,
                    'file_size': first_version_size,
                    'file_version_size_sum': osf_storage_file.total_file_size,
                    'file_last_seen': osf_storage_file.last_touched.isoformat(),  # TODO - what property should this be?
                    'node_guid': target._id,
                    'node_type': target.type,
                    'node_is_fork': getattr(target, 'is_fork', None),
                    'node_is_public': getattr(target, 'is_public', None),
                    'node_is_deleted': is_deleted,
                }
            )
            progress_bar.update(added)

    return file_csv


if __name__ == '__main__':
    utils.add_file_logger(logger, __file__)

    if '--raw' in sys.argv:
        file_csv = generate_raw_csv()
        filename = os.path.join(EXPORT_PATH, 'osfstorage_file_assessment_raw_numbers.csv.gz')
    else:
        file_csv = do_evaulation()
        filename = os.path.join(EXPORT_PATH, 'osfstorage_file_assessment.csv.gz')

    with gzip.GzipFile(filename=filename, mode='wb') as gzip_obj:
        gzip_obj.write(file_csv.getvalue())
