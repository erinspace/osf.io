# script to create lots of projects, users, registrations, and everything

import random
import logging
from faker import Faker

from website.app import setup_django, init_app
init_app()
setup_django()

from django.db.models.aggregates import Count
from django_bulk_update.helper import bulk_update
from django.core.paginator import Paginator

from framework.auth import Auth
from framework.auth.utils import impute_names_model

from scripts.create_fakes import create_fake_project, create_fake_filename, create_fake_sentence
from osf_tests.factories import UserFactory, ProjectFactory, RegistrationFactory, NodeFactory, IdentifierFactory, NodeLogFactory, PreprintFactory
from api_tests.utils import create_test_file
from osf.models import OSFUser, Node, Registration, PreprintProvider, Conference, Subject, Identifier, NodeLog
from addons.wiki.models import NodeWikiPage
from website import settings

from addons.osfstorage.models import OsfStorageFile


PUBLIC_PROJECT_GOAL = 27113
PRIVATE_PROJECT_GOAL = 51158
COMPONENT_GOAL = 82656
REGISTRATION_GOAL = 13808
NODE_LOG_GOAL = 9431910
USER_GOAL = 115685

BASE_FILE_NODE_GOAL = 4380945
OSFSTORAGE_FILE_NODE_GOAL = 3364299
OSFSTORAGE_FILE_GOAL = 2710536

PREPRINT_PER_PROVIDER_GOAL = 50
SUBJECTS_PER_PREPRINT = 5
PER_CONFERENCE_GOAL = 50
WIKI_WITH_CONTENT_GOAL = 5000
IDENTIFIER_GOAL = 5000

HTML_WIKI_CONTENT = """
<h1>HELLO</h1>

<p><b>This is a wiki with HTML in it.</b></p>
    """

MARKDOWN_WIKI_CONTENT = """
# What's Up

    markdown is where it's at
    """

PLAINTEXT_WIKI_CONTENT = "Just plain text yeah cool"
NAME_FIELDS = ['given_name', 'middle_names', 'family_name', 'suffix', 'fullname']


logger = logging.getLogger(__name__)
fake = Faker()




def get_privacy(privacy):
    if privacy == 'random':
        is_public = random.choice([True, False])
    elif privacy == 'public':
        is_public = True
    else:
        is_public = False

    return is_public


def rename_all_bulk_stress_test_project_just_because_it_annoys_me():
    bulk_projects = Node.objects.filter(title__icontains='bulk stress')
    total = bulk_projects.count()
    total_updated = 0
    paginated_bulk_projects = Paginator(bulk_projects, 10)
    for page_num in paginated_bulk_projects.page_range:
        projects_to_update = []
        for project in paginated_bulk_projects.page(page_num).object_list:
            title = create_fake_sentence()
            project.title = title
            # logger.info('Renamed bulk stress project {} with title {}'.format(project._id, title))
            projects_to_update.append(project)
            total_updated += 1
        bulk_update(projects_to_update, update_fields=['title'])
        logger.info('Updated {}/{} bulk projects'.format(total_updated, total))


def give_users_named_freddie_more_interesting_names():
    freddie_users = OSFUser.objects.filter(fullname__contains='Freddie Mercury')
    total = freddie_users.count()
    total_updated = 0
    paginated_bulk_users = Paginator(freddie_users, 1000)
    for page_num in paginated_bulk_users.page_range:
        users_to_update = []
        for user in paginated_bulk_users.page(page_num).object_list:
            fullname = fake.name()
            user.fullname = fullname
            parsed = impute_names_model(fullname)
            for key, value in parsed.items():
                setattr(user, key, value)
            users_to_update.append(user)
            total_updated += 1
        bulk_update(users_to_update, update_fields=NAME_FIELDS)
        logger.info('Updated {}/{} bulk users formerly named freddie'.format(total_updated, total))



def get_random_existing_user():
    count = OSFUser.objects.filter(is_active=True).aggregate(count=Count('id'))['count']
    random_index = random.randint(0, count - 1)
    return OSFUser.objects.filter(is_active=True)[random_index]


def get_random_existing_toplevel_project(privacy='random'):
    is_public = get_privacy(privacy)
    count = Node.objects.filter(_parents__isnull=True, is_deleted=False, is_public=is_public).aggregate(count=Count('id'))['count']
    random_index = random.randint(0, count - 1)
    return Node.objects.filter(_parents__isnull=True, is_deleted=False, is_public=is_public)[random_index]


def get_random_existing_project_at_any_level(privacy='random', creator=None):
    is_public = get_privacy(privacy)
    filters = {
        'is_deleted': False,
        'is_public': is_public
    }
    if creator:
        filters['creator'] = creator

    count = Node.objects.filter(**filters).aggregate(count=Count('id'))['count']
    try:
        random_index = random.randint(0, count - 1)
    except ValueError:
        ProjectFactory(creator=creator, is_public=is_public)
        random_index = 0

    return Node.objects.filter(**filters)[random_index]


def get_random_subject(provider, force_root=False):
    filters = {
        'provider': provider
    }
    if force_root:
        filters['parent__isnull'] = True

    count = Subject.objects.filter(**filters).aggregate(count=Count('id'))['count']
    random_index = random.randint(0, count-1)
    return Subject.objects.filter(**filters)[random_index]


def get_random_preprint_provider():
    # It is ok to use order_by ? here because there are relatively few preprint providers
    return PreprintProvider.objects.order_by('?').first()


def user_that_does_things(projects=3):
    user = UserFactory(fullname=fake.name())
    auth = Auth(user=user)
    privacy = ['private', 'private', 'public']

    component_structures = [
        0,             # project with 0 components
        1,             # project with 1 component
        [1, 1, 1, 1],  # project with 4 components
        [1, [1, 1]],   # project with 2 components, 1 is 2 levels deep
        3              # project with 1 component, 3 levels deep
    ]

    for p in range(projects):
        project = create_fake_project(
            creator=user,
            n_users=0,
            privacy=random.choice(privacy),
            n_components=random.choice(component_structures),
            name=None,
            n_tags=random.randint(0, 5),
            presentation_name=None,
            is_registration=False,
            is_preprint=False,
            preprint_provider=None
        )

        # pick a few existing users to add as contributors
        number_of_contributors = random.randint(0, 5)

        for _ in range(number_of_contributors):
            if random.choice([True, False]):
                user = get_random_existing_user()
            else:
                user = UserFactory(fullname=fake.name())
            project.add_contributor(user, auth=auth)


def simple_user_that_does_things():
    user = UserFactory(fullname=fake.name())
    project = ProjectFactory(creator=user, is_public=random.choice([True, False, False]))
    logger.info('User {} Created project {} which is public? {}'.format(user.fullname, project.title, project.is_public))

def just_the_user():
    user = UserFactory(fullname=fake.name())
    logger.info('Hello {}'.format(user.fullname))

# Files
def create_fake_files():
    while OsfStorageFile.objects.filter(deleted_by__isnull=True).count() < OSFSTORAGE_FILE_GOAL:
        project = get_random_existing_project_at_any_level()

        for _ in range(0, random.randint(1, 20)):
            filename = create_fake_filename()
            try:
                create_test_file(project, project.creator, filename=filename)
                logger.info('Created file with name {} for project with guid {}'.format(filename, project._id))
            except Exception as e:
                logger.info('Ran into exception: {}, moving along...'.format(e))
                break


# Conferences
def populate_conference(conference):
    # projects_to_update = []
    while Node.objects.filter(tags__name=conference.endpoint, is_deleted=False, is_public=True).count() < PER_CONFERENCE_GOAL:
        project = get_random_existing_toplevel_project(privacy='public')
        auth = Auth(project.creator)
        project.add_tag(conference.endpoint, auth=auth, save=False)
        # projects_to_update.append(project)
        project.save()
        logger.info('Marked project with guid {} with tag {}'.format(project._id, conference.endpoint))


    # bulk_update(projects_to_update, update_fields=['tags'])

# Wiki
def write_wiki_content():
    project = get_random_existing_project_at_any_level()
    auth = Auth(project.creator)
    project.update_node_wiki(
        'home',
        random.choice([PLAINTEXT_WIKI_CONTENT, MARKDOWN_WIKI_CONTENT, HTML_WIKI_CONTENT]),
        auth
    )

    # Add another page on a few of them
    if random.choice([True, False, False]):
        project.update_node_wiki('woo', random.choice([PLAINTEXT_WIKI_CONTENT, MARKDOWN_WIKI_CONTENT, HTML_WIKI_CONTENT]), auth)

    logger.info('Updated project with guid {} with content'.format(project._id))


# Preprints
def create_some_preprints(provider):
    if provider.subjects.count():
        logger.info('Trying to add preprints to {}'.format(provider._id))
        while provider.preprint_services.count() < PREPRINT_PER_PROVIDER_GOAL:
            creator = get_random_existing_user()
            if creator.nodes_created.filter(is_public=True, is_deleted=False).count() > 1:
                project = get_random_existing_project_at_any_level(privacy='public', creator=creator)
                if project.preprints.count():
                    project = ProjectFactory(creator=creator, is_public=True)
            else:
                project = ProjectFactory(creator=creator, is_public=True)

            try:
                preprint = PreprintFactory(
                    provider=provider,
                    creator=creator,
                    project=project,
                    subjects=[[get_random_subject(provider, force_root=True)._id]]
                )
            except Exception as e:
                logger.info('Got exception: {}, moving along...'.format(e))
                continue

            subjects = [get_random_subject(provider) for _ in range(SUBJECTS_PER_PREPRINT)]
            for sub in subjects:
                preprint.subjects.add(sub)
                preprint.save()
            logger.info('Created preprint with guid {} on provider with _id {}'.format(preprint._id, provider._id))


# Projects
def bulk_create_projects(batch_size=10, is_public=True):
    projects_to_create = []
    for i in range(batch_size):
        project = ProjectFactory._build(target_class=Node, creator=get_random_existing_user(), is_public=is_public)
        projects_to_create.append(project)

    Node.objects.bulk_create(projects_to_create)
    type = 'public' if is_public else 'private'
    logger.info('Bulk created {} {} projects'.format(batch_size, type))
    # bulk_update(projects_to_create)


# Identifiers
def create_fake_identifiers():
    while Identifier.objects.count() < IDENTIFIER_GOAL:
        try:
            project = get_random_existing_project_at_any_level(privacy='public')
            fake_doi = '{doi}osf.io/{guid}'.format(doi=settings.DOI_NAMESPACE, guid=project._id)
            identifier = IdentifierFactory(referent=project, value=fake_doi, category='doi')
            logger.info('Created an identifier {} on project {}'.format(identifier.value, project._id))
        except Exception:
            logger.info('Error on project {}, identifier {} already exists'.format(project._id, identifier.value))
            pass

# Node logs
def create_node_logs():
    project = get_random_existing_project_at_any_level()
    action = random.choice([choice[0] for choice in NodeLog.action_choices])
    NodeLogFactory(action=action, user=project.creator)
    logger.info('Created log on project {} with action {}'.format(project._id, action))


def create_registration_from_existing_projects():
    project = get_random_existing_toplevel_project()
    try:
        registration = RegistrationFactory(creator=project.creator, project=project)
        logger.info('Created registration {} from project {}'.format(registration._id, project.title))
    except Exception as e:
        logger.error('Ran into exception {}, moving along...'.format(e))


def create_component():
    is_public = random.choice([True, False, False])
    project = get_random_existing_toplevel_project()
    comp = NodeFactory(parent=project, is_public=is_public, creator=project.creator)
    for _ in range(0, random.randint(1, 10)):
        filename = create_fake_filename()
        try:
            create_test_file(comp, comp.creator, filename=filename)
            logger.info('Created file with name {} for comp with guid {}'.format(filename, project._id))
        except Exception as e:
            logger.info('Ran into exception: {}, moving along...'.format(e))
            break
    logger.info('Made component {} from parent titled {}'.format(comp._id, project.title))


def run_metrics():
    logger.info('Here is what we have to do:')
    logger.info('We need to make {} more users'.format(USER_GOAL - OSFUser.objects.filter(is_active=True).count()))
    logger.info('We need to make {} more public projects'.format(PUBLIC_PROJECT_GOAL - Node.objects.filter(is_public=True, _parents__isnull=True, is_deleted=False).count()))
    logger.info('We need to make {} more private projects'.format(PRIVATE_PROJECT_GOAL - Node.objects.filter(is_public=False, _parents__isnull=True, is_deleted=False).count()))
    logger.info('We need to make {} more components'.format(COMPONENT_GOAL - Node.objects.filter(_parents__isnull=False, is_deleted=False).count()))
    logger.info('We need to make {} more registrations'.format(REGISTRATION_GOAL - Registration.objects.filter(is_deleted=False).count()))
    logger.info('We need to make {} more wikis have content'.format(WIKI_WITH_CONTENT_GOAL - NodeWikiPage.objects.exclude(content='').count()))
    logger.info('We need to make {} more files'.format(OSFSTORAGE_FILE_GOAL - OsfStorageFile.objects.filter(deleted_by__isnull=True).count()))
    logger.info('We need to make {} more identifiers'.format(IDENTIFIER_GOAL - Identifier.objects.count()))


def main():
    # rename_all_bulk_stress_test_project_just_because_it_annoys_me()
    # give_users_named_freddie_more_interesting_names()

    run_metrics()

    # first get all the users we want and some other stuff too
    logger.info('Ensuring we have at least {} users...'.format(USER_GOAL))
    while OSFUser.objects.filter(is_active=True).count() < USER_GOAL:
        just_the_user()
        # if random.choice([True, False, False, False, False, False]):
        #     user_that_does_things()
        # else:
        #     simple_user_that_does_things()

    # Now try for the public project goal
    logger.info('Ensuring we have at least {} public projects...'.format(PUBLIC_PROJECT_GOAL))
    while Node.objects.filter(is_public=True, _parents__isnull=True, is_deleted=False).count() < PUBLIC_PROJECT_GOAL:
        user = get_random_existing_user()
        logger.info('About to make a project for user {}, with username {}'.format(user._id, user.username))
        ProjectFactory(creator=user, is_public=True)
        # bulk_create_projects()

    # Now try for the private project goal
    logger.info('Ensuring we have at least {} private projects...'.format(PRIVATE_PROJECT_GOAL))
    while Node.objects.filter(is_public=False, _parents__isnull=True, is_deleted=False).count() < PRIVATE_PROJECT_GOAL:
        ProjectFactory(creator=get_random_existing_user(), is_public=False)
        # bulk_create_projects(is_public=False)

    # try for component goal
    logger.info('Ensuring we have at least {} components...'.format(COMPONENT_GOAL))
    while Node.objects.filter(_parents__isnull=False, is_deleted=False).count() < COMPONENT_GOAL:
        create_component()

    # Populate conferences with existing projects
    logger.info('Ensuring we have at least {} projects in every conference'.format(PER_CONFERENCE_GOAL))
    for conference in Conference.objects.filter(active=True, is_meeting=True):
        populate_conference(conference)

    # Populate existing project wikis with content
    logger.info('Ensuring we have at least {} wikis with content...'.format(WIKI_WITH_CONTENT_GOAL))
    while NodeWikiPage.objects.exclude(content='').count() < WIKI_WITH_CONTENT_GOAL:
        write_wiki_content()

    # Preprints
    logger.info('Ensuring we have at least {} preprints in each provider...'.format(PREPRINT_PER_PROVIDER_GOAL))
    for provider in PreprintProvider.objects.all():
        create_some_preprints(provider)

    # Files
    create_fake_files()

    # Identifiers
    create_fake_identifiers()

    # try for registration goal
    logger.info('Ensuring we have at least {} registrations...'.format(REGISTRATION_GOAL))
    while Registration.objects.filter(is_deleted=False).count() < REGISTRATION_GOAL:
        create_registration_from_existing_projects()

    # node logs
    logger.info('About to try for {} node logs, and there are {}'.format(NODE_LOG_GOAL, NodeLog.objects.count()))
    while NodeLog.objects.count() < NODE_LOG_GOAL:
        create_node_logs()

if __name__=='__main__':
    main()
