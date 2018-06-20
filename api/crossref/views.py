import logging

import lxml.etree
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.crossref.permissions import RequestComesFromMailgun
from framework.auth.views import mails
from osf.models import PreprintService
from website import settings

logger = logging.getLogger(__name__)


class ParseCrossRefConfirmation(APIView):
    # This view goes under the _/ namespace
    view_name = 'parse_crossref_confirmation_email'
    view_category = 'identifiers'

    permission_classes = (
        RequestComesFromMailgun,
    )

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(ParseCrossRefConfirmation, self).dispatch(request, *args, **kwargs)

    def get_serializer_class(self):
        return None

    def post(self, request):
        crossref_email_content = lxml.etree.fromstring(str(request.POST['body-plain']))
        status = crossref_email_content.get('status').lower()  # from element doi_batch_diagnostic
        record_count = int(crossref_email_content.find('batch_data/record_count').text)
        records = crossref_email_content.xpath('//record_diagnostic')
        dois_processed = 0

        if status == 'completed':
            for record in records:
                doi = getattr(record.find('doi'), 'text', None)
                guid = doi.split('/')[-1] if doi else None
                if record.get('status').lower() == 'success' and doi:
                    msg = record.find('msg').text
                    created = bool(msg == 'Successfully added')
                    preprint = PreprintService.load(guid)
                    if created:
                        # Sets preprint_doi_created, don't save to avoid sending duplicate metadata?
                        preprint.set_identifier_values(doi=doi, save=True)
                    else:
                        # Directly updates the identifier
                        preprint.set_identifier_value(category='doi', value=doi)

                    logger.info('Creation success email received from CrossRef for preprint {}'.format(preprint._id))
                    dois_processed += 1

                    # Mark legacy DOIs overwritten by newly batch confirmed crossref DOIs
                    legacy_doi = preprint.get_identifier(category='legacy_doi')
                    if legacy_doi:
                        legacy_doi.remove()

        if dois_processed != record_count or status != 'completed':
            first_guid = crossref_email_content.find('batch_id').text.split(',')[0]
            preprint = PreprintService.load(first_guid)
            mails.send_mail(
                to_addr=settings.OSF_SUPPORT_EMAIL,
                mail=mails.CROSSREF_ERROR,
                preprint=preprint,
                doi=settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id),
                email_content=request.POST['body-plain'],
            )
            logger.error('Error submitting metadata for preprint {} with CrossRef, email sent to help desk'.format(preprint._id))

        return HttpResponse('Mail received', status=200)
