from couchdbkit.exceptions import DocTypeError


def schema_map(schema, dynamic_properties):
    if hasattr(schema, "wrap") and hasattr(schema, '_doc_type'):
        schema = {schema._doc_type: schema}
    elif isinstance(schema, list):
        schema = dict((s._doc_type, s) for s in schema)

    if dynamic_properties is not None:
        for name, cls in schema.items():
            if cls._allow_dynamic_properties != dynamic_properties:
                schema[name] = type(cls.__name__, (cls,), {
                    '_allow_dynamic_properties': dynamic_properties,
                })
    return schema


def doctype_attr_of(classes):
    doc_type_attrs = set(cls._doc_type_attr for cls in classes)
    assert len(doc_type_attrs) == 1, "inconsistent doctype attr"
    return doc_type_attrs.pop()


def get_multi_wrapper(classes):
    doctype_attr = doctype_attr_of(classes.values())

    def wrap(doc):
        doc_type = doc.get(doctype_attr)
        try:
            cls = classes[doc_type]
        except KeyError:
            raise DocTypeError(
                "the document being wrapped has doc type {0!r}. "
                "To wrap it anyway, you must explicitly pass in "
                "classes={{{0!r}: <document class>}} to your view. "
                "This behavior is new starting in 0.6.2.".format(doc_type)
            )
        return cls.wrap(doc)

    return wrap


def schema_wrapper(schema, dynamic_properties=None):
    if hasattr(schema, "wrap") and hasattr(schema, '_doc_type') and not dynamic_properties:
        return schema.wrap
    mapping = schema_map(schema, dynamic_properties)
    return get_multi_wrapper(mapping)


def maybe_schema_wrapper(schema, params):
    dynamic_properties = params.pop('dynamic_properties', None)
    return schema_wrapper(schema, dynamic_properties)
