import re
from enum import Enum

import networkx as nx
from matplotlib import pyplot as plt

pattern_gate_app = r'^\s*([\w\s,]+)\s*=\s*([\w\s,]+\([\w\s,]+\))\s*$'
pattern_init = r'^(\s*\w+\s*(\s*,\s*\w+)*)\s*=\s*qubit\(\s*\)(\s*,\s*qubit\(\s*\))*'
pattern_measure = r'\w'
node_count = 1
exit_node = 'Exit'
start_node = 'Start'


class EdgeLabel:
    def __init__(self, type_label, value):
        self.value = value
        self.type = type_label

    def __str__(self):
        return str(self.type).split(".")[1] + ": " + str(self.value)

    def __repr__(self):
        return self.__str__()


class NodeType(Enum):
    Args = 1
    GateCall = 2
    Measure = 3
    NonZero = 4
    Zero = 5
    Skip = 6
    Ret = 7
    Init = 8
    Discard = 9


def print_cfg(cfg, print_details):
    """
    plots the cfg
    :param cfg: control flow graph
    :param print_details: id true we print the list of nodes and edges
    """
    print(type(cfg))
    if print_details:
        print(cfg.nodes)
        print(cfg.edges.data("label"))
    pos = nx.spring_layout(cfg)
    labels = nx.get_edge_attributes(cfg, 'label')
    nx.draw(cfg, pos, with_labels=True, node_size=300, node_color="lightblue", font_size=8, font_color="black",
            font_weight="bold", arrows=True)
    nx.draw_networkx_edge_labels(cfg, pos, edge_labels=labels, font_size=7)
    plt.title("Control Flow Graph with Edge Labels")
    plt.show()


def clean_var_names(var_names):
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    return [string for string in var_names if bool(re.match(pattern, string)) and string != '_']


def count_tab(string):
    count = 0
    for char in string:
        if char == ' ':
            count += 1
        else:
            break  
    return count


def reset_count():
    global node_count
    node_count = 1


def new_node():
    global node_count
    node = str(node_count)
    node_count = node_count + 1
    return node


def extract_variables(declaration):
    '''
    :type declaration: str
    '''
    sub1 = declaration.split('(')[1]
    sub2 = sub1.split(')')[0]
    pat = r'\b(\w+)\s*:'
    matches = re.findall(pat, sub2)
    return matches


def extract_function_name(string):
    pattern1 = r'^(\w+)(?=\()'
    match = re.match(pattern1, string)

    return match.group(1)


def extract_function_args(string):
    pattern2 = r'\((.*?)\)'
    match = re.search(pattern2, string)
    if match:
        variables = match.group(1).split(',')
        return [var.strip() for var in variables]
    else:
        return []


def extract_sub_graph(cfg, lines, head_node, end_node, tabs):  #, if_branch_size, , tabs):
    branch_lines = []
    end_index = 0
    for line in lines:
        # print(line)
        if count_tab(line) > tabs:
            branch_lines.append(line)
            end_index += 1
        else:
            break

    branch_cfg = nx.DiGraph()
    branch_cfg.add_node(head_node)
    branch_cfg = build_cfg(branch_lines, branch_cfg, head_node)

    branch_end_nodes = [node for node in branch_cfg.nodes if branch_cfg.out_degree(node) == 0]
    cfg = nx.compose(cfg, branch_cfg)
    for branch_end_node in branch_end_nodes:
        if branch_end_node != exit_node:
            cfg = nx.relabel_nodes(cfg, {branch_end_node: end_node})

    return cfg, lines[end_index:]


def build_cfg(lines, cfg=None, prev_node=None):
    global exit_node
    if len(lines) == 0:
        return cfg
    l = lines[0]
    if 'def' in lines[0]:
        # def fun(x: qubit, v: qubit , _, )...:
        graph = nx.DiGraph()
        reset_count()
        graph.add_node(start_node)
        graph.add_node(exit_node)
        args = clean_var_names(extract_variables(lines[0]))
        # ['x','y',]
        p_node = new_node()
        graph.add_edge(start_node, p_node, label=EdgeLabel(NodeType.Args, args))
        fun_name = lines[0].replace(" ", "").split('(')[0][3:]

        return fun_name, build_cfg(lines[1:], graph, p_node)

    if 'pass' in lines[0]:
        p_node = new_node()
        cfg.add_node(p_node)
        cfg.add_edge(prev_node, p_node, label=EdgeLabel(NodeType.Skip, ''))

        return build_cfg(lines[1:], cfg, p_node)

    if 'return' in lines[0]:
        # return x,y,_,...
        ret_vars = clean_var_names(lines[0].replace(" ", "").replace("\n", "")[6:].split(','))
        cfg.add_edge(prev_node, exit_node, label=EdgeLabel(NodeType.Ret, ret_vars))

        return cfg

    if 'discard' in lines[0]:
        # discard(x,y,...)
        p_node = new_node()
        cfg.add_node(p_node)
        cfg.add_edge(prev_node, p_node,
                     label=EdgeLabel(NodeType.Discard, lines[0].replace(" ", "").replace("\n", "")[8:-1].split(',')))
        return build_cfg(lines[1:], cfg, p_node)

    if 'measure' in lines[0]:
        # _ = measure(x,y,...)
        p_node = new_node()
        cfg.add_node(p_node)
        part = lines[0].replace(" ", "").replace("\n", "").split('=')
        m_vars = clean_var_names(part[1][8:-1].split(','))
        cfg.add_edge(prev_node, p_node, label=EdgeLabel(NodeType.Measure, m_vars))
        return build_cfg(lines[1:], cfg, p_node)

    if 'if' in lines[0]:
        tabs = count_tab(lines[0])
        cond = lines[0].replace(" ", "").replace("\n", "")[2:-1]
        if_node = new_node()
        cfg.add_node(if_node)
        cfg.add_edge(prev_node, if_node,
                     label=EdgeLabel(NodeType.NonZero, cond))
        end_node = new_node()
        cfg.add_node(end_node)
        cfg, lines_after_if = extract_sub_graph(cfg, lines[1:], if_node, end_node, tabs)

        if len(lines_after_if) > 0 and 'else' in lines_after_if[0]:
            else_node = new_node()
            cfg.add_node(else_node)
            cfg.add_edge(prev_node, else_node, label=EdgeLabel(NodeType.Zero, cond))
            cfg, lines_after_if = extract_sub_graph(cfg, lines_after_if[1:], else_node, end_node, tabs)
        else:
            cfg.add_edge(prev_node, end_node, label=EdgeLabel(NodeType.Zero, cond))

        return build_cfg(lines_after_if, cfg, end_node)

    if 'while' in lines[0] or 'for' in lines[0]:
        tabs = count_tab(lines[0])
        if 'while' in lines[0]:
            # while cond:
            cond = lines[0].replace(" ", "").replace("\n", "")[5:-1]
        else:
            # for v in cond:
            cond = lines[0].replace(" ", "").replace("\n", "")[3:-1]
            cond = cond.replace('in', ' ')
        while_node = new_node()
        cfg.add_node(while_node)
        cfg.add_edge(prev_node, while_node, label=EdgeLabel(NodeType.NonZero, cond))

        cfg, lines_after_while = extract_sub_graph(cfg, lines[1:], while_node, prev_node, tabs)

        end_node = new_node()
        cfg.add_node(end_node)
        cfg.add_edge(prev_node, end_node, label=EdgeLabel(NodeType.Zero, cond))

        return build_cfg(lines_after_while, cfg, end_node)

    if re.match(pattern_gate_app, lines[0]):
        # x,y = gate(x,y)
        p_node = new_node()
        cfg.add_node(p_node)
        part = lines[0].replace(" ", "").split('=')

        out_vars = clean_var_names(part[0].split(","))
        fun_name = extract_function_name(part[1])
        in_vars = clean_var_names(extract_function_args(part[1]))

        cfg.add_edge(prev_node, p_node, label=EdgeLabel(NodeType.GateCall, [out_vars, fun_name, in_vars]))

        return build_cfg(lines[1:], cfg, p_node)

    if re.match(pattern_init, lines[0]):
        # x,y,... = qubit(),qubit(),...
        p_node = new_node()
        cfg.add_node(p_node)
        part = lines[0].replace(" ", "").split('=')

        cfg.add_edge(prev_node, p_node, label=EdgeLabel(NodeType.Init, part[0].split(",")))

        return build_cfg(lines[1:], cfg, p_node)

    exit('error parsing: ' + l)

