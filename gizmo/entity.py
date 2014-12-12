from field import String, DateTime, Boolean, List, Map, _Fields, Field
from utils import get_qualified_name, get_qualified_instance_name, TYPES, IMMUTABLE
from utils import GIZMO_MODEL, GIZMO_CREATED, GIZMO_MODIFIED, GIZMO_NODE_TYPE, GIZMO_TYPE, GIZMO_ID, GIZMO_LABEL
from utils import current_date_time

#Holds the model->object mappings
_MAP = {}


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
            
            self.fields = _Fields({
                GIZMO_MODEL     : String(get_qualified_instance_name(self), data_type=data_type),
                GIZMO_CREATED   : DateTime(value=current_date_time, data_type=data_type, set_max=1),
                GIZMO_MODIFIED  : DateTime(value=current_date_time, data_type=data_type),
                GIZMO_NODE_TYPE : String(self._node_type, data_type=data_type),
                GIZMO_ID        : String(data_type=data_type),
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
                self.fields[GIZMO_LABEL] = String(label, data_type=data_type)
            
            #build the properties for the instance
            for name, field in attrs.iteritems():
                if not name.startswith('_'):
                    if isinstance(field, Field):
                        instance = field.__class__(field.value, field.data_type)
                        self.fields[name] = instance
                    else:
                        setattr(self, name, field)

            self.data_type = 'python'

            self.hydrate(data)
        
            if data is not None and GIZMO_ID in data:
                self.fields[GIZMO_ID].field_value = data[GIZMO_ID]
            
            self.dirty = False
    
        attrs['__init__'] = new_init__
        cls = super(_RootEntity, cls).__new__(cls, name, bases, attrs)
        map_name = '%s.%s' % (cls.__module__, cls.__name__)
        _MAP[map_name] = cls
        
        return cls


class _BaseEntity(object):
    __metaclass__ = _RootEntity
    immutable = IMMUTABLE['vertex']
    allow_undefined = False
    
    def hydrate(self, data=None):
        if data is None:
            data = {}
        
        for field, value in data.iteritems():
            self[field] = value
        
        return self
    
    def _add_undefined_field(self, name, value):
        if type(value) is dict:
            field = Map(value, self.data_type)
        elif type(value) is list:
            field = List(value, self.data_type)
        else:
            field = String(value, self.data_type)
        
        self.fields[name] = field
        
        return field
    
    def __setitem__(self, name, value):
        if name not in self.immutable and name in self.fields:
            self.fields[name].value = value
            self.dirty = True
        elif self.allow_undefined:
            self._add_undefined_field(name, value)
            self.dirty = True
        
        return self
        
    def __getitem__(self, name):
        value = None

        if name in self.fields:
            value = self.fields[name].value
        elif self.allow_undefined:
            field = self._add_undefined_field(name, value)
            
        return value
        
    def _get_data_type(self):
        return self.data_type
        
    def _set_data_type(self, data_type):
        self.data_type = data_type
        self.fields.data_type = data_type
    
    field_type = property(_get_data_type, _set_data_type)
    
    @property
    def _node_type(self):
        raise NotImplementedError('Vertices and Edges need a _node_type defined')
        
    @property
    def data(self):
        return self.fields.data
        
    def get_rep(self):
        entity = 'e' if self._type == 'edge' else 'v'
        
        return entity, self['_id']


class Vertex(_BaseEntity):
    @property
    def _type(self):
        return 'vertex'


class GenericVertex(Vertex):
    allow_undefined = True

    @property
    def _node_type(self):
        return 'generic_vertex'


class Edge(_BaseEntity):
    immutable = IMMUTABLE['edge']

    @property
    def _type(self):
        return 'edge'


class GenericEdge(Edge):
    allow_undefined = True

    @property
    def _node_type(self):
        return 'generic_edge'