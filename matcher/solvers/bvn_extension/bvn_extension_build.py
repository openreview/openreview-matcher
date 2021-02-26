'''
Provides instructions for building the extension containing the sampling procedure for RandomizedSolver.
'''

from cffi import FFI

ffibuilder = FFI()

header = "int run_bvn(double* flows, int* subsets, int nrevs, int npaps);"
ffibuilder.cdef(header)
ffibuilder.set_source("_bvn_extension", # extension name
    header,
    sources=['matcher/solvers/bvn_extension/bvn.c'],
    libraries=['m'])  # link with the math library

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
