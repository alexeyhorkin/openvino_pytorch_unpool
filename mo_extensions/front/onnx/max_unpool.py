# mo_extensions/front/onnx/max_unpool.py
import numpy as np

from mo.front.common.replacement import FrontReplacementSubgraph
from mo.graph.graph import Graph
from mo_extensions.ops.MaxPoolGrad import MaxPoolGrad
from mo.front.onnx.extractors.utils import onnx_attr

class MaxUnpool(FrontReplacementSubgraph):
    enabled = True

    def pattern(self):
        return dict(
            nodes=[
                ('input', dict()),
                ('max_pool0', dict(op='MaxPool')),
                ('max_pool1', dict(op='MaxPool')),
                ('slice', dict(op='Slice')),
                ('sub', dict(op='Sub')),
                ('unpool', dict(op='Unpooling')),
            ],
            edges=[
                ('input', 'max_pool0'),
                ('input', 'max_pool1'),
                ('max_pool1', 'slice'),
                ('max_pool0', 'sub', {'in': 0}),
                ('slice', 'sub', {'in': 1}),
                ('sub', 'unpool', {'in': 1}),
            ])

    @staticmethod
    def replace_sub_graph(graph: Graph, match: dict):
        max_pool_input = match['input']
        max_pool = match['max_pool0']
        unpool = match['unpool']
        unpool_input = unpool.in_port(0).get_source().node

        max_pool.out_port(1).disconnect()

        # Inputs: [max_pool_input, max_pool_output, unpool_input]
        res = MaxPoolGrad(graph, dict(name=unpool.name + '/fused')).create_node([max_pool_input, max_pool, unpool_input])
        unpool.out_port(0).get_connection().set_source(res.out_port(0))

        output_size = onnx_attr(unpool, 'output_size', 'ints', default=None)
        if output_size:
            MaxPoolGrad.update_node_stat(res, attrs = { 'output_size': output_size })
