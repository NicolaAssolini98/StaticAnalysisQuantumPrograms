

# Static Analysis of Quantum Programs
Code for the SAS 2024 paper: "Static Analysis Quantum Programs"

> In principle, the design and implementation of quantum programming languages are the same essential tasks as for conventional (classical) programming languages. High-level programming constructs and compilation tools are structurally similar in both cases. The difference is mainly in the hardware machine executing the final code, which in the case of quantum programming languages is a quantum processor, i.e. a physical object obeying the laws of quantum mechanics. Therefore, special technical solutions are required to comply with such laws. In this paper, we show how static analysis can guarantee the correct implementation of quantum programs by introducing two data-flow analyses for detecting some ‘wrong‘ uses of quantum variables. A compiler including such analyses would allow for a higher level of abstraction in the quantum language, relieving the programmer of low-level tasks such as the safe removal of temporary variables.

## Getting Started

This code requires only `networkx` and `matplotlib` libraries to be executed
To test the prototype, execute the `main.py` file.

We consider a simple program languages inspired by [Guppy](https://github.com/CQCL/guppylang), with some simplifications.
In particular, we cannot write:

    if measure(q):

but we have to write:

    r = measure(q)
    if r:
    

Moreover, we don't consider inline functions as

    q = h(qubit())
    p = h(x(q))
    
but we have to write:

    t1 = qubit()
    q = h(t1)
    t2 = x(q)    
    p = h(t2)    
    

Our pipeline is thought to be inserted in the compilation process, after having filtered all non-relevant part of the program.
All classical variables must be marked as `_`, so that they are ignored by the analysis
Finally, we consider a simplified CFG, so no `break` or `continue`.

`\test` contains a txt file with some small examples, the programs analyse only function decorated with `@guppy` decorator.
In the example, we write, as comments, the errors that must be generated or where we must add the discard functions.


## Contributors
*  **Nicola Assolini** - nicola.assolini@univr.it

## Reference

[//]: # ([Static Analysis of Quantum Programs]&#40;&#41;)
```
@inproceedings{assolini2024static,
  title={Static Analysis of Quantum Programs},
  author={Assolini, Nicola and Di Pierro, Alessandra and Mastroeni, Isabella},
  booktitle={Static Analysis: 31th International Symposium, SAS 2024, Pasadena, USA, October 20-22, 2024. Proceedings},
  year={2024},
  organization={Springer}
}
```


