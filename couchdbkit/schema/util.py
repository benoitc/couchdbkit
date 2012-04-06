

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


def get_multi_wrapper(classes):

    def wrap(doc):
        doc_type = doc.get('doc_type')
        cls = classes[doc_type]
        return cls.wrap(doc)

    return wrap


def schema_wrapper(schema, dynamic_properties=None):
    mapping = schema_map(schema, dynamic_properties)
    return get_multi_wrapper(mapping)


def maybe_schema_wrapper(wrapper, schema, params):
    dynamic_properties = params.pop('dynamic_properties', None)
    return wrapper or schema_wrapper(schema, dynamic_properties)
