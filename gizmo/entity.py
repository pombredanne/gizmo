from inspect import isfunction
from copy import copy, deepcopy

from six import with_metaclass

from .field import (String, DateTime, List, Integer, Float, Map, _Fields,
                    Field, Enum, Timestamp, Mirror)
from .utils import (get_qualified_instance_name, IMMUTABLE, GIZMO_MODEL,
                    GIZMO_CREATED, GIZMO_LABEL, GIZMO_MODIFIED, GIZMO_ID,
                    current_date_time, camel_to_underscore)


# Holds the model->object mappings
_MAP = {}
DEFAULT_MODEL_FIELDS = [
    GIZMO_MODEL,
    GIZMO_CREATED,
    GIZMO_MODIFIED,
    GIZMO_ID,
]


class _RootEntity(type):
    """
    maps all models during definition to their object so that it can be
    loaded later
    overwrites the __init__ method. Models cannot define one
    """

    def __new__(cls, name, bases, attrs):

        def new_init__(self, data=None, data_type='python'):
            if data is None:
                data = {}

            data = copy(data)
            self.data_type = data_type

            if hasattr(self, '_node_label'):
                cls_label = self._node_label
            else:
                cls_label = str(self)

            data[GIZMO_LABEL] = cls_label

            if '_allowed_undefined' in attrs:
                self._allowed_undefined = attrs['_allowed_undefined']

            if '_atomic_changes' in attrs:
                self._atomic_changes = attrs['_atomic_changes']

            # the modified field is a microsecond later than the created
            # this is done for testing purposes
            def modified():
                return current_date_time(1)

            self.fields = _Fields({
                GIZMO_MODEL: String(get_qualified_instance_name(self),
                                    data_type=data_type, track_changes=False),
                GIZMO_CREATED: DateTime(value=current_date_time,
                                        data_type=data_type,
                                        set_max=1, track_changes=False),
                GIZMO_MODIFIED: Timestamp(value=modified,
                                         data_type=data_type,
                                         track_changes=False),
                GIZMO_LABEL: String(cls_label, data_type=data_type,
                                    track_changes=False),
                GIZMO_ID: String(data_type=data_type,
                                 track_changes=False),
            })

            if isinstance(self, Edge):
                if 'out_v' in data:
                    self.out_v = data['out_v']

                    del data['out_v']
                else:
                    self.out_v = None

                if '_outV' in data:
                    self.outV = data['_outV']

                    del data['_outV']
                else:
                    self.outV = None

                if 'in_v' in data:
                    self.in_v = data['in_v']

                    del data['in_v']

                if '_inV' in data:
                    self.inV = data['_inV']

                    del data['_inV']
                else:
                    self.inV = None

                label = data.get('label', None)

                if label is None:
                    label = cls_label

                self.fields[GIZMO_LABEL] = String(value=label,
                                                  data_type=data_type)

            """"
            build the properties for the instance
            ignore things that start with an underscore and methods
            this is done for all of the bases first, then the actual model
            """
            undefined = deepcopy(data)

            def update_fields(obj):
                for name, field in obj.items():
                    if not name.startswith('_'):
                        if isinstance(field, Field):
                            value = field._initial_value
                            kwargs = {
                                'value': value,
                                'data_type': field.data_type,
                                'set_max': field.set_max,
                                'track_changes': field.track_changes,
                            }

                            if isinstance(field, Enum):
                                kwargs['allowed'] = field.allowed
                            elif isinstance(field, Mirror):
                                kwargs['fields'] = field.fields
                                kwargs['callback'] = field.callback

                            instance = field.__class__(**kwargs)
                            self.fields[name] = instance
                        elif (type(field) is not property
                              and not isfunction(field)):
                            setattr(self, name, field)

            def handle(handle_bases):
                handle_dict = {}

                for base in handle_bases:
                    if isinstance(base, _RootEntity):
                        handle_dict.update(handle(base.__bases__))

                    handle_dict.update(base.__dict__)

                return handle_dict

            update_fields(handle(bases))
            update_fields(attrs)
            self.hydrate(undefined)

            if data is not None and GIZMO_ID in data:
                self.fields[GIZMO_ID].field_value = data[GIZMO_ID]

        attrs['__init__'] = new_init__
        cls = super(_RootEntity, cls).__new__(cls, name, bases, attrs)
        map_name = '%s.%s' % (cls.__module__, cls.__name__)
        _MAP[map_name] = cls

        return cls


class _BaseEntity(with_metaclass(_RootEntity, object)):
    _immutable = IMMUTABLE['vertex']
    _allowed_undefined = False
    _atomic_changes = False

    def hydrate(self, data=None):
        if data is None:
            data = {}

        for field, value in data.items():
            self[field] = value

        return self

    def __getitem__(self, name):
        return self.fields.get(name, self._allowed_undefined)

    def __setitem__(self, name, value):
        if name not in self._immutable:
            self.fields.set(name, value, self._allowed_undefined)

        return self

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return camel_to_underscore(self.__class__.__name__)

    def _get_data_type(self):
        return self.data_type

    def _set_data_type(self, data_type):
        self.data_type = data_type
        self.fields.data_type = data_type

    field_type = property(_get_data_type, _set_data_type)

    def get_rep(self):
        entity = 'E' if self._type == 'edge' else 'V'

        return entity, self['_id']

    @property
    def data(self):
        return self.fields.data

    @property
    def label(self):
        return self.__getitem__(GIZMO_LABEL)

    @property
    def changed(self):
        return self.fields.changed

    @property
    def unchanged(self):
        return self.fields.unchanged

    @property
    def removed(self):
        return self.fields.removed


class Vertex(_BaseEntity):
    _type = 'vertex'


class GenericVertex(Vertex):
    _allowed_undefined = True


class Edge(_BaseEntity):
    _type = 'edge'
    _immutable = IMMUTABLE['edge']


class GenericEdge(Edge):
    _allowed_undefined = True
