from modularodm import Q


PREREG_CAMPAIGNS = {
    'prereg': 'Prereg Challenge',
    'erpc': 'Election Research Preacceptance Competition',
}

def drafts_for_user(user, campaign):
    from website import models  # noqa

    user_projects = models.Node.objects.filter(is_deleted=False, contributor__admin=True, contributor__user=user)
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema(campaign)
    return models.DraftRegistration.objects.filter(
        registration_schema=PREREG_CHALLENGE_METASCHEMA,
        approval=None,
        registered_node=None,
        branched_from__in=[p.id for p in user_projects]
    )

def get_prereg_schema(campaign='prereg'):
    from website.models import MetaSchema  # noqa
    if campaign not in PREREG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(PREREG_CAMPAIGNS.keys())))
    schema_name = PREREG_CAMPAIGNS[campaign]

    return MetaSchema.find_one(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', 2)
    )
