import networkx as nx
import matplotlib.pyplot as plt

from cfg_build import build_cfg, print_cfg
from parser import obtain_function, clean_empty_line_and_comment
from analysis import (consuming_analysis, uncomputation_analysis, consuming_check, insert_discard)

debug = True


file_path = 'txt_files/test_2'
# file_path = 'txt_files/test_entangled'
tag = '@guppy'
groups = obtain_function(file_path)
# for group in groups:
#     print('----')
#     print(group)


for group in groups:
    code = clean_empty_line_and_comment(group)
    name, cfg = build_cfg(code)
    print(name, ':')
    print(cfg)
    print_cfg(cfg, True)

    d_cal = consuming_analysis(cfg)
    print('Available vars for each node:\n\t %s' % d_cal)
    dup_tuples = consuming_check(cfg, d_cal)
    if len(dup_tuples) > 0:
        print('ERROR, used not defined/consumed variable')
        print('not defined/consumed used vars: %s' % dup_tuples)
    else:
        pairs = uncomputation_analysis(cfg)
        uncomputation = insert_discard(cfg, pairs)
        print('Uncomputation analysis results:')
        print('\t%s' % pairs)
        print('Discard must be added in these program points:\n\t%s' %
              uncomputation if len(uncomputation) > 0 else 'not discard function is needed')

    print('----------------')
    #break

# consider_discard = True
# print(entaglement_analysis(g, consider_discard))
