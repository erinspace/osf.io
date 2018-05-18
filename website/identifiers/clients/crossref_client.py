# -*- coding: utf-8 -*-
import furl
import lxml
import time
import requests
from framework.exceptions import HTTPError

from website.identifiers.metadata import remove_control_characters
from website.util.client import BaseClient
from website import settings


class CrossRefClient(BaseClient):

    BASE_URL = settings.CROSSREF_DEPOSIT_URL

    def build_doi(self, node):
        from osf.models import PreprintService, PreprintProvider

        namespace = settings.EZID_DOI_NAMESPACE
        if isinstance(node, PreprintService):
            namespace = node.provider.doi_prefix or PreprintProvider.objects.get(_id='osf').doi_prefix
        return settings.CROSSREF_DOI_FORMAT.format(namespace=namespace, guid=node._id)

    def build_metadata(self, preprint, **kwargs):
        """Return the crossref metadata XML document for a given preprint as a string for DOI minting purposes

        :param preprint -- the preprint
        """

        doi = self.build_doi(preprint)
        if kwargs.get('status', '') == 'unavailable':
            return ''

        element = lxml.builder.ElementMaker(nsmap={
            None: settings.CROSSREF_NAMESPACE,
            'xsi': settings.XSI},
        )

        head = element.head(
            element.doi_batch_id(preprint._id),
            # TODO -- CrossRef has said they don't care about this field, is this OK?
            element.timestamp('{}'.format(int(time.time()))),
            element.depositor(
                element.depositor_name(settings.CROSSREF_DEPOSITOR_NAME),
                element.email_address(settings.CROSSREF_DEPOSITOR_EMAIL)
            ),
            element.registrant(preprint.provider.name)  # TODO - confirm provider name is desired
        )

        posted_content = element.posted_content(
            element.group_title(preprint.provider.name),
            element.contributors(*self._crossref_format_contributors(element, preprint)),
            element.titles(element.title(preprint.node.title)),
            element.posted_date(*self._crossref_format_date(element, preprint.date_published)),
            element.item_number('osf.io/{}'.format(preprint._id)),
            type='preprint'
        )

        if preprint.node.description:
            posted_content.append(
                element.abstract(element.p(preprint.node.description), xmlns=settings.JATS_NAMESPACE))

        if preprint.license and preprint.license.node_license.url:
            posted_content.append(
                element.program(
                    element.license_ref(preprint.license.node_license.url,
                                        start_date=preprint.date_published.strftime('%Y-%m-%d')),
                    xmlns=settings.CROSSREF_ACCESS_INDICATORS
                )
            )

        if preprint.node.preprint_article_doi:
            posted_content.append(
                element.program(
                    element.related_item(
                        element.intra_work_relation(
                            preprint.node.preprint_article_doi,
                            **{'relationship-type': 'isPreprintOf', 'identifier-type': 'doi'}
                        ),
                        xmlns=settings.CROSSREF_RELATIONS
                    )
                )
            )

        doi_data = [
            element.doi(doi),
            element.resource(settings.DOMAIN + preprint._id)
        ]
        posted_content.append(element.doi_data(*doi_data))

        root = element.doi_batch(
            head,
            element.body(posted_content),
            version=settings.CROSSREF_SCHEMA_VERSION
        )
        # set xsi:schemaLocation
        root.attrib['{%s}schemaLocation' % settings.XSI] = settings.CROSSREF_SCHEMA_LOCATION
        return lxml.etree.tostring(root, pretty_print=kwargs.get('pretty_print', True))

    def _crossref_format_contributors(self, element, preprint):
        contributors = []
        for index, contributor in enumerate(preprint.node.visible_contributors):
            if index == 0:
                sequence = 'first'
            else:
                sequence = 'additional'

            person = element.person_name(sequence=sequence, contributor_role='author')
            contributor_given_plus_middle = remove_control_characters(
                ' '.join([contributor.given_name, contributor.middle_names]).strip()
            )
            person.append(element.given_name(contributor_given_plus_middle))
            person.append(element.surname(remove_control_characters(contributor.family_name)))
            if contributor.suffix:
                person.append(element.suffix(remove_control_characters(contributor.suffix)))

            contributors.append(person)

        return contributors

    def _crossref_format_date(self, element, date):
        elements = [
            element.month(date.strftime('%m')),
            element.day(date.strftime('%d')),
            element.year(date.strftime('%Y'))
        ]
        return elements

    def _make_request(self, method, url, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)

        response = requests.request(method, url, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code, message=response.content)

        return response

    def _build_url(self, **query):
        url = furl.furl(self.BASE_URL)
        url.args.update(query)
        return url.url

    def create_identifier(self, metadata, doi):
        filename = doi.split('/')[-1]

        # When this request is made in production Crossref sends an email our mailgun account at
        # CROSSREF_DEPOSITOR_EMAIL, to test locally create your own mailgun account and forward the
        # message to the 'crossref' endpoint. You use ngrok to tunnel out so your local enviroment
        # can replicate the whole process.
        self._make_request(
            'POST',
            self._build_url(
                operation='doMDUpload',
                login_id=settings.CROSSREF_USERNAME,
                login_passwd=settings.CROSSREF_PASSWORD,
                fname='{}.xml'.format(filename)
            ),
            files={'file': ('{}.xml'.format(filename), metadata)},
            expects=(200, )
        )

        # Don't wait for response to confirm doi because it arrives via email.
        return {'doi': doi}

    def change_status_identifier(self, status, metadata, identifier):
        return self.create_identifier(metadata, identifier)
