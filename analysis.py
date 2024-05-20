import copy
from enum import Enum
from functools import reduce

import networkx as nx

from cfg_build import NodeType, exit_node

# To disable debug print in this file
debug = True


def disable_print(*args, **kwargs):
    pass


if not debug:
    print = disable_print


class Value(Enum):
    Bot = 1
    Z = 2
    X = 3
    Y = 4
    XY = 5
    YZ = 6
    XZ = 7
    S = 8
    Top = 9


relation = [
    (Value.Bot, Value.Z),
    (Value.Bot, Value.X),
    (Value.Bot, Value.Y),
    (Value.Z, Value.XZ),
    (Value.Z, Value.YZ),
    (Value.X, Value.XY),
    (Value.X, Value.XZ),
    (Value.Y, Value.XY),
    (Value.Y, Value.YZ),
    (Value.XY, Value.S),
    (Value.S, Value.Top),
    (Value.XZ, Value.Top),
    (Value.YZ, Value.Top)
]
cpo = nx.DiGraph()
cpo.add_edges_from(relation)

def get_all_vars(cfg):
    all_vars = set()
    for _, _, data in cfg.edges(data=True):
        label = data['label']
        inst_type = label.type
        instr = label.value
        if (inst_type == NodeType.Args or inst_type == NodeType.Init or inst_type == NodeType.Ret or
                inst_type == NodeType.Discard or inst_type == NodeType.Measure):
            # ['arg1', 'arg2']
            all_vars.update(instr)
        elif inst_type == NodeType.GateCall:
            # [['out1', 'out2'], 'cx', ['in1', 'in2']]
            all_vars.update(instr[0])
            all_vars.update(instr[2])

    return all_vars


def consuming_analysis(cfg):
    all_vars = get_all_vars(cfg)
    avs = {node: all_vars for node in cfg.nodes()}

    get_all_vars(cfg)
    fixpoint = False
    while not fixpoint:
        old_avs = {node: avs[node].copy() for node in avs.keys()}
        for node in cfg.nodes():
            temps_avs = []
            predecessors = list(cfg.predecessors(node))
            for pred in predecessors:
                added_vars = set()
                removed_vars = set()
                label = cfg[pred][node]["label"]
                inst_type = label.type
                instr = label.value
                if inst_type == NodeType.Args or inst_type == NodeType.Init:
                    # ['arg1', 'arg2']
                    added_vars.update(instr)
                elif inst_type == NodeType.Ret or inst_type == NodeType.Discard or inst_type == NodeType.Measure:
                    # ['arg1', 'arg2']
                    removed_vars.update(instr)
                elif inst_type == NodeType.GateCall:
                    # [['out1', 'out2'], 'cx', ['in1', 'in2']]
                    added_vars.update(instr[0])
                    removed_vars.update(instr[2])
                temp_avs = old_avs[pred] - removed_vars
                temp_avs.update(added_vars)
                temps_avs.append(temp_avs)

            avs[node] = reduce(lambda x, y: x & y, temps_avs) if len(temps_avs) > 0 else set()
        fixpoint = old_avs == avs

    return avs


def consuming_check(cfg, avs_vars):
    """
    returns a list of triple:
    (node, edge, variable) thats indicates the node in which we find the error, the edge (i.e. the instruction) that
    generates it, and the variables that are used not properly
    """
    error_list = []
    for edge in cfg.edges:
        label = cfg[edge[0]][edge[1]]["label"]
        inst_type = label.type
        instr = label.value
        if inst_type == NodeType.Ret or inst_type == NodeType.Discard or inst_type == NodeType.Measure:
            # ['arg1', 'arg2']
            if not (set(instr) <= avs_vars[edge[0]]):
                cons_vars = set(instr).difference(avs_vars[edge[0]])
                error_list.append((edge[0], edge, cons_vars))
                print('Instr %s at node %s used %s after consumption' % (instr, edge[0], cons_vars))
        elif inst_type == NodeType.GateCall:
            # [['out1', 'out2'], 'g', ['in1', 'in2']]
            if not (set(instr[2]) <= avs_vars[edge[0]]):
                cons_vars = set(instr[2]).difference(avs_vars[edge[0]])
                error_list.append((edge[0], edge, cons_vars))
                print('Instr %s at node %s used %s after consumption' % (instr, edge[0], cons_vars))

    return error_list


def lub_2_pairs(pair1, pair2):
    safe_intersection = pair1[0] & pair2[0]
    unsafe_union = pair1[1] | pair2[1] | (pair1[0] ^ pair2[0])

    return safe_intersection, unsafe_union


def uncomputation_analysis(cfg):
    # (safe, unsafe)
    pairs = {node: None for node in cfg.nodes()}
    pairs[exit_node] = (set(), set())

    fixpoint = False
    while not fixpoint:
        #print(pairs)
        old_pairs = {node: copy.deepcopy(pairs[node]) if pairs[node] is not None else None for node in pairs.keys()}
        for node in list(cfg.nodes()):
            temps_pairs = []
            successors = list(cfg.successors(node))
            for suc in successors:
                added_vars = set()
                removed_vars = set()
                label = cfg[node][suc]["label"]
                inst_type = label.type
                instr = label.value
                if inst_type == NodeType.Args or inst_type == NodeType.Init:
                    # ['arg1', 'arg2']
                    removed_vars.update(instr)
                elif inst_type == NodeType.Ret or inst_type == NodeType.Discard or inst_type == NodeType.Measure:
                    # ['arg1', 'arg2']
                    added_vars.update(instr)
                elif inst_type == NodeType.GateCall:
                    # [['out1', 'out2'], 'cx', ['in1', 'in2']]
                    added_vars.update(instr[2])
                    removed_vars.update(instr[0])

                if old_pairs[suc] is not None:
                    temp_safe = old_pairs[suc][0] - removed_vars
                    temp_unsafe = old_pairs[suc][1] - removed_vars
                    temp_safe.update(added_vars)
                    temps_pairs.append((temp_safe, temp_unsafe))

            if len(temps_pairs) > 0:
                lub = reduce(lambda x, y: lub_2_pairs(x, y), temps_pairs)
            elif len(successors) == 0:
                lub = old_pairs[node]
            else:
                lub = None
            pairs[node] = lub

        fixpoint = (old_pairs == pairs)

    return pairs


def get_all_definition(cfg, var):
    # used for checking consumption
    def_edges = set()
    for u, v, data in cfg.edges(data=True):
        label = data['label']
        inst_type = label.type
        instr = label.value
        if inst_type == NodeType.Init or inst_type == NodeType.Args:
            # ['arg1', 'arg2']
            if var in instr:
                def_edges.add((u, v))
        elif inst_type == NodeType.GateCall:
            # [['out1', 'out2'], 'cx', ['in1', 'in2']]
            if var in instr[0]:
                def_edges.add((u, v))

    return def_edges


def insert_discard(cfg, pairs):
    """
    :param cfg:
    :param pairs: (S,U) for each node
    :param vars_to_uncompute: list of variable to uncompute

    return a list couples, containing the edges in which we have to uncompute variables,
     and the variable that we need to uncompute
    """
    uncompute_position = []
    all_unsafe = set()
    for node in cfg.nodes():
        all_unsafe.update(pairs[node][1])

    for var in get_all_vars(cfg):
        for u, v in get_all_definition(cfg, var):
            if var not in pairs[v][0] and var not in pairs[v][1]:
                uncompute_position.append(((u, v), var))



    for var in all_unsafe:
        for node in cfg.nodes():
            # we consider the node only where var in unsafe
            if var in pairs[node][1]:
                for v in cfg.successors(node):
                    if var not in pairs[v][0] and var not in pairs[v][1]:
                        uncompute_position.append(((node, v), var))

    return uncompute_position
    val1 = abs_dom.get_store_val(in_vars[0])

    if fun == 'x' or fun == 'y' or fun == 'z':
        pass  # abs_dom.update_value(in_vars[0], val1)

    elif fun == 'h':
        if len(abs_dom.get_set(in_vars[0])) == 1:
            if val1 == Value.Bot or val1 == Value.Y or val1 == Value.XZ:
                pass  # abs_dom.update_value(in_vars[0], val1)
            elif val1 == Value.Z:
                abs_dom.update_value(in_vars[0], Value.X)
            elif val1 == Value.X:
                abs_dom.update_value(in_vars[0], Value.Z)
            elif val1 == Value.XY:
                abs_dom.update_value(in_vars[0], Value.YZ)
            elif val1 == Value.YZ:
                abs_dom.update_value(in_vars[0], Value.XY)
            else:
                abs_dom.update_value(in_vars[0], Value.Top)
        else:
            if val1 == Value.Bot:
                pass  # abs_dom.update_value(in_vars[0], val1)
            else:
                abs_dom.update_value(in_vars[0], Value.Top)

    elif fun == 's' or fun == 'sdg':
        if val1 == Value.Z or val1 == Value.XY or val1 == Value.S or val1 == Value.Bot:
            pass  # abs_dom.update_value(in_vars[0], val1)
        elif val1 == Value.Y:
            abs_dom.update_value_set(in_vars[0], Value.X)
        elif val1 == Value.X:
            abs_dom.update_value_set(in_vars[0], Value.Y)
        elif val1 == Value.YZ:
            abs_dom.update_value_set(in_vars[0], Value.XZ)
        elif val1 == Value.XZ:
            abs_dom.update_value_set(in_vars[0], Value.YZ)
        else:
            abs_dom.update_value(in_vars[0], Value.Top)

    elif fun == 't' or fun == 'tdg':
        if val1 == Value.Z or val1 == Value.S or val1 == Value.Bot:
            pass  # abs_dom.update_value(in_vars[0], val1)
        elif val1 == Value.X or val1 == Value.Y:
            abs_dom.update_value_set(in_vars[0], Value.S)
        else:
            abs_dom.update_value(in_vars[0], Value.Top)

    elif fun == 'rx':
        if len(abs_dom.get_set(in_vars[0])) == 1 and (val1 == Value.X or val1 == Value.Bot):
            pass  # abs_dom.update_value(in_vars[0], val1)
        else:
            abs_dom.update_value(in_vars[0], Value.Top)

    elif fun == 'rz':
        if val1 == Value.Z or val1 == Value.Bot or val1 == Value.S:
            pass  # abs_dom.update_value(in_vars[0], val1)
        if val1 == Value.X or val1 == Value.Y or val1 == Value.XY:
            abs_dom.update_value(in_vars[0], Value.S)
        else:
            abs_dom.update_value(in_vars[0], Value.Top)

    elif fun == 'cx':
        ctrl = in_vars[0]
        targ = in_vars[1]
        v_c = abs_dom.get_store_val(ctrl)
        v_t = abs_dom.get_store_val(targ)
        if len(abs_dom.get_set(targ)) == 1:
            if v_c == Value.Z or v_t == Value.X or v_c == Value.Bot or v_t == Value.Bot:
                pass
            elif (v_c == Value.X or v_c == Value.Y or v_c == Value.S) and v_t == Value.Z:
                abs_dom.set_entagled_on_value(v_c, ctrl, targ)
            else:
                abs_dom.set_entagled_on_value(Value.Top, ctrl, targ)

        elif len(abs_dom.get_set(targ)) > 1:
            if (v_c == Value.Z or v_c == Value.Bot or v_t == Value.Bot) and abs_dom.is_disjoint(ctrl, targ):
                pass
            elif abs_dom.is_disjoint(ctrl, targ):
                abs_dom.set_entagled_on_value(Value.Top, ctrl, targ)
                abs_dom.update_value_set(ctrl, Value.Top)
            elif not abs_dom.is_disjoint(ctrl, targ):
                if ((v_c == Value.X or v_c == Value.Y or v_c == Value.S) and
                        (v_t == Value.X or v_t == Value.Y or v_t == Value.S)):
                    abs_dom.disentagled(ctrl, targ)
                else:
                    abs_dom.update_value(ctrl, Value.Top)
                    abs_dom.update_value(targ, Value.Top)

    elif fun == 'cz':
        ctrl = in_vars[0]
        targ = in_vars[1]
        v_c = abs_dom.get_store_val(ctrl)
        v_t = abs_dom.get_store_val(targ)
        if v_c == Value.Z or v_c == Value.Z or v_c == Value.Bot or v_t == Value.Bot:
            # redundant, if value(q) = Z then len(abs_dom.get_set(q) = 1
            # and (len(abs_dom.get_set(targ)) == 1 or len(abs_dom.get_set(ctrl)) == 1)):
            pass
        else:
            abs_dom = abs_semantics('h', abs_dom, in_vars[1:])
            abs_dom = abs_semantics('cx', abs_dom, in_vars)
            abs_dom = abs_semantics('h', abs_dom, in_vars[1:])


    elif fun == 'measure':
        for var in in_vars:
            var_val = abs_dom.get_store_val(var)
            if var_val == Value.X or var_val == Value.Y or var_val == Value.XY or var_val == Value.S:
                ent_with_var = copy.deepcopy(abs_dom.get_set(var))
                for vv in ent_with_var:
                    if vv != var:
                        # in this case al variables collapse to Value.Z
                        if abs_dom.get_store_val(vv) == var_val:
                            abs_dom.update_value(vv, Value.Z)
                            abs_dom.remove_from(var, vv)
            if var_val == Value.Top:
                ent_with_var = copy.deepcopy(abs_dom.get_set(var))
                for vv in ent_with_var:
                    if vv != var:
                        abs_dom.update_value(vv, Value.Top)

            abs_dom.delete_var(var)

    return abs_dom

