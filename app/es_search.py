from flask import current_app


def add_to_index(index, model):
    """
    add to es and  modify a record through `id`
    :param index: es index
    :param model: db.Model
    :return: None
    """
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id,
                                    body=payload)


def remove_from_index(index, model):
    """
    remove record from es through model
    :param index: es index
    :param model: db.Model
    :return: None
    """
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    """
    query something from es
    :param index: index name
    :param query: query key
    :param page: current page
    :param per_page: records-count/page
    :return: [ids] of records, total
    """
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
