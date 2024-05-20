
This scrip requires only `networkx` and `matplotlib` libraries to be executed

To test the prototype execute the `main.py` file.

The directory `test` contains a txt file with some small examples, the programs analyse only function decorated with `@guppy` decorator.

`print_cfg` plots the cfg
`consuming_analysis` execute the consuming analysis, 
`consuming_check` checks the correctness of the programs
`uncomputation_analysis` perform the analysis of uncomputation
`insert_discard` insert the discard function using the information from previous analysis

We made some simplification to Guppy programs, in particular, """

we cannot write:

    if measure(bla):

we have to write:

    r = measure(bla)
    if r:
    

we don't consider inline function:

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


In the example we write, as comments, the errors that must be generated or where me must add the discard functions
