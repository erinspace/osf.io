# -*- coding: utf-8 -*-

import time
import bleach
import logging
from urllib2 import HTTPError

from flask import request
from modularodm import Q

from framework import status
from framework.auth.core import get_current_user
from framework.auth.decorators import must_be_logged_in

import website.search.search as search
from website.models import User, Node
from website.project.views.contributor import get_node_contributors_abbrev


logger = logging.getLogger(__name__)


def search_search():
    tick = time.time()
    ERROR_RETURN = {
        'results': [],
        'tags': [],
        'query': '',
    }
    # search results are automatically paginated. on the pages that are
    # not the first page, we pass the page number along with the url
    start = request.args.get('pagination', 0)
    try:
        start = int(start)
    except (TypeError, ValueError):
        logger.error(u'Invalid pagination value: {0}'.format(start))
        start = 0
    query = request.args.get('q')
    # if there is not a query, tell our users to enter a search
    query = bleach.clean(query, tags=[], strip=True)
    if query == '':
        status.push_status_message('No search query', 'info')
        return ERROR_RETURN

    # if the search does not work,
    # post an error message to the user, otherwise,
    # the document, highlight,
    # and spellcheck suggestions are returned to us
    try:
        results_search, tags, counts = search.search(query, start)
    except HTTPError:
        status.push_status_message('Malformed query. Please try again')
        return ERROR_RETURN
    except TypeError:
        status.push_status_message('There was a problem querying the search database. Please try again later.')
        return ERROR_RETURN

    # with our highlights and search result 'documents' we build the search
    # results so that it is easier for us to display
    # Whether or not the user is searching for users
    searching_users = query.startswith("user:")
    total = counts if not isinstance(counts, dict) else counts['total']
    return {
        'highlight': [],
        'results': results_search,
        'total': total,
        'query': query,
        'spellcheck': [],
        'current_page': start,
        'time': round(time.time() - tick, 2),
        'tags': tags,
        'searching_users': searching_users,
        'counts': counts
    }


@must_be_logged_in
def search_projects_by_title(**kwargs):
    # TODO(fabianvf): At some point, it would be nice to do this with elastic search

    term = request.args.get('q')
    if not term:
        return {'results': [], 'count': 0}

    user = kwargs['auth'].user

    max_results = 10

    matching_title = (
        Q('title', 'icontains', term) &  # search term (case insensitive)
        Q('category', 'eq', 'project') &  # is a project
        Q('is_deleted', 'eq', False)  # isn't deleted
    )

    my_projects = Node.find(
        matching_title &
        Q('contributors', 'contains', user._id)  # user is a contributor
    ).limit(max_results)

    if my_projects.count() < max_results:
        public_projects = Node.find(
            matching_title &
            Q('is_public', 'eq', True)  # is public
        ).limit(max_results - my_projects.count())
    else:
        public_projects = []

    results = list(my_projects) + list(public_projects)

    out = []

    for project in results:
        authors = get_node_contributors_abbrev(project=project, auth=kwargs['auth'])
        authors_html = ''
        for author in authors['contributors']:
            a = User.load(author['user_id'])
            authors_html += '<a href="%s">%s</a>' % (a.url, a.fullname)
            authors_html += author['separator'] + ' '
        authors_html += ' ' + authors['others_count']
        if authors['others_count']:
            authors_html += ' other' + authors['others_suffix']

        out.append({
            'id': project._id,
            'label': project.title,
            'value': project.title,
            'category': 'My Projects' if user in project.contributors else 'Public Projects',
            'authors': authors_html,
        })

    return {'results': out, 'count': len(out)}


def search_contributor():
    nid = request.args.get('excludeNode')
    exclude = Node.load(nid).contributors if nid else list()
    query = bleach.clean(request.args.get('query', ''), tags=[], strip=True)
    return search.search_contributor(query, exclude, get_current_user())
