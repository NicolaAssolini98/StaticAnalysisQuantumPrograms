
This script requires only `networkx` and `matplotlib` libraries to be executed

To test the prototype, execute the `main.py` file.

The directory `test` contains a txt file with some small examples, the programs analyse only function decorated with `@guppy` decorator.

`print_cfg` plots the cfg
`consuming_analysis` executes the consuming analysis, 
`consuming_check` checks the correctness of the programs
`uncomputation_analysis` performs the analysis of uncomputation
`insert_discard` inserts the discard function using the information from the previous analysis

We made some simplifications to Guppy programs, in particular, 
we cannot write:

    if measure(bla):

we have to write:

    r = measure(bla)
    if r:
    

we don't consider inline functions:

    q = h(qubit())

or

    p = h(x(q))
    
we have to write:

    t = qubit()
    q = h(t)
or

    t = x(q)    
    p = h(t)    
    
   
    
We must always assign when using quantum functions, apart from discard, so we cannot write things likes

    measure(q)

This constraint comes from Guppy.

Our pipeline is thought to be inserted in the compilation process, after having filtered all non-relevant part of the program.
All classical variables must be marked as `_`, so that they are ignored by the analysis

Finally, we consider a simplified CFG, so no break or continue

In the example, we write, as comments, the errors that must be generated or where we must add the discard functions
