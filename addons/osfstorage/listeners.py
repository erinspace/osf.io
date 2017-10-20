'''
Listens for actions to be done to OSFstorage file nodes specifically.
'''


from website.project.signals import contributor_removed

@contributor_removed.connect
def checkin_files_by_user(node, user):
    ''' Listens to a contributor being removed to check in all of their files
    '''
    from django.contrib.contenttypes.models import ContentType
    from addons.osfstorage.models import OsfStorageFileNode
    content_type = ContentType.objects.get_for_model(node)
    OsfStorageFileNode.objects.filter(object_id=node.id, content_type=content_type, checkout=user).update(checkout=None)
