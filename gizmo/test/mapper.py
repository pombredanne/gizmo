import unittest
from random import randrange, random
from collections import OrderedDict
from gizmo.mapper import Mapper, Vertex, Edge
from gizmo.request import _Request
from gizmo.utils import GIZMO_MODEL, GIZMO_CREATED, GIZMO_MODIFIED, GIZMO_NODE_TYPE, GIZMO_TYPE, GIZMO_ID, GIZMO_LABEL
from gremlinpy.gremlin import Gremlin
from entity import TestVertex, TestEdge, TestUndefinedVertex
import copy


def get_dict_key(params, value, unset=False):
    for k, v in params.iteritems():
        if v == value:
            if unset:
                del(params[k])
            return k, params

    return None, dict


def get_entity_entry(entity_queue, entity):
    for i, s in entity_queue.iteritems():
        if s == entity:
            return {i: entity_queue[i]}

    return None


class TestRequest(_Request):
    pass


DEFAULT_INSERT_FIELDS = [
    GIZMO_MODEL,
    GIZMO_CREATED,
    GIZMO_MODIFIED,
    GIZMO_NODE_TYPE,
]

DEFAULT_UPDATE_FIELDS = [GIZMO_ID] + DEFAULT_INSERT_FIELDS


class MapperTests(unittest.TestCase):
    def setUp(self):
        self.gremlin = Gremlin()
        self.request = TestRequest('localhost', 'x', 'x')
        self.mapper = Mapper(self.request, self.gremlin)

    def get_model_data(self, data, model):
        seed = random()
        d = {
            GIZMO_MODEL     : 'some_model_%s' % seed,
            GIZMO_CREATED   : 'some_created_%s' % seed,
            GIZMO_MODIFIED  : 'some_mod_%s' % seed,
            GIZMO_NODE_TYPE : 'some_node_type_%s' % seed,
        }

        if edge:
            d[GIZMO_LABEL] = 'some_label_%s' % seed

        if id is not None:
            d[GIZMO_ID] = id

        return OrderedDict(sorted(d.items()))

    def test_mapper_instance(self):
        m = Mapper(self.gremlin, self.request)

        self.assertTrue(type(m) == Mapper)

    def test_can_create_vertex(self):
        v = self.mapper.create_model(model_class=TestVertex)

        self.assertTrue(isinstance(v, Vertex))
        self.assertEquals(v._type, 'vertex')

    def test_can_create_vertex_with_data(self):
        d = {'some_field': random()}
        v = self.mapper.create_model(d, TestVertex)
        vd = v.data

        """
        the entity's data will have a _type member
        """
        self.assertTrue(isinstance(v, Vertex))

        for k, v in d.iteritems():
            self.assertIn(k, vd)
            self.assertEqual(v, vd[k])

    def test_can_update_existing_vertex(self):
        vid = 1111
        d = {
            GIZMO_ID: vid,
            'some_field': 'mark',
        }
        v = self.mapper.create_model(d, TestVertex)
        self.mapper.save(v)._build_queries()

        params = self.mapper.params
        sent_params = copy.deepcopy(self.mapper.params)
        immutable = v.immutable
        query_ps = []
        entry_v1 = get_entity_entry(self.mapper.models, v)
        v.field_type = 'graph'

        for k, v in v.data.iteritems():
            if k not in immutable:
                value, paramsss = get_dict_key(params, v)
                prop = "it.setProperty('%s', %s)" % (k, value)
                query_ps.append(prop)

        propv, params = get_dict_key(sent_params, vid)

        close = '._().sideEffect{%s}.next()' % '; '.join(query_ps)
        params = (entry_v1.keys()[0], propv, close)
        expected = "%s = g.v(%s)%s" % params

        self.assertEqual(expected, self.mapper.queries[0])
        self.assertEqual(len(d) + len(DEFAULT_INSERT_FIELDS), len(sent_params))

    def test_can_queue_save_vertex_with_two_params_query(self):
        d = {
            'some_field': 'mark',
        }
        v = self.mapper.create_model(d, TestVertex)

        self.mapper.save(v)._build_queries()

        params = copy.deepcopy(self.mapper.params)
        sent_params = copy.deepcopy(self.mapper.params)

        immutable = v.immutable
        props = []
        entry_v1 = get_entity_entry(self.mapper.models, v)
        v.field_type = 'graph'

        for k,v in v.data.iteritems():
            if k not in immutable:
                value, params = get_dict_key(params, v, True)
                prop = "'%s': %s" % (k, value)
                props.append(prop)

        expected = "%s = g.addVertex([%s])" % (entry_v1.keys()[0] ,', '.join(props))

        self.assertEqual(expected, self.mapper.queries[0])
        self.assertEqual(len(d) + len(DEFAULT_INSERT_FIELDS), len(sent_params))

    def test_can_create_edge_with_existing_vertices(self):
        v1 = self.get_model_data({}, id=15)
        v2 = self.get_model_data({}, id=10)
        out_v = self.mapper.create_model(v1, TestVertex)
        in_v = self.mapper.create_model(v2, TestVertex)
        ed = {'out_v': out_v, 'in_v': in_v}
        edge = self.mapper.create_model(ed, TestEdge)

        self.assertTrue(isinstance(edge, Edge))
        self.assertTrue(isinstance(edge.out_v, TestVertex))
        self.assertTrue(isinstance(edge.in_v, TestVertex))

    def test_can_queue_save_edge_with_existing_vertices(self):
        v1 = self.get_model_data({}, id=15)
        v2 = self.get_model_data({}, id=10)
        out_v = self.mapper.create_model(v1, TestVertex)
        in_v = self.mapper.create_model(v2, TestVertex)
        ed = {'out_v': out_v, 'in_v': in_v, '_label': 'knows'}
        edge = self.mapper.create_model(ed, TestEdge)

        self.mapper.save(edge)._build_queries()

        print self.mapper.queries

class QueryTests(unittest.TestCase):
    def setUp(self):
        self.gremlin = Gremlin()
        self.request = TestRequest('localhost', 'x', 'x')
        self.mapper = Mapper(self.request, self.gremlin)

    def test_query_wont_save_model_twice(self):
        print 'xxxx'


class EventSourceTests(unittest.TestCase):
    def setUp(self):
        pass


if __name__ == '__main__':
    unittest.main()
