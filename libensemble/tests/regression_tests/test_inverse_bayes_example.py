# """
# Runs libEnsemble on the 6-hump camel problem. Documented here:
#    https://www.sfu.ca/~ssurjano/camel6.html
#
# Execute via the following command:
#    mpiexec -np 4 python3 inverse_bayes_example.py
#    mpiexec -np 4 xterm -e "python3 inverse_bayes_example.py"
# The number of concurrent evaluations of the objective function will be 4-1=3.
# """

from __future__ import division
from __future__ import absolute_import

import sys, os             # for adding to path
import numpy as np
import pdb

from libensemble.libE import libE

nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
is_master = True
if len(sys.argv) > 1 and sys.argv[1] == "--threads":
    libE_specs = {'nthreads': nworkers}
elif len(sys.argv) > 1 and sys.argv[1] == "--processes":
    libE_specs = {'nprocesses': nworkers}
else:
    from mpi4py import MPI
    nworkers = MPI.COMM_WORLD.Get_size()-1
    is_master = MPI.COMM_WORLD.Get_rank() == 0
    libE_specs = {'comm': MPI.COMM_WORLD, 'color': 0}

# Import sim_func
from libensemble.sim_funcs.inverse_bayes import likelihood_calculator as sim_f

# Import gen_func
from libensemble.gen_funcs.persistent_inverse_bayes import persistent_updater_after_likelihood as gen_f

# Import alloc_func
from libensemble.alloc_funcs.inverse_bayes_allocf import only_persistent_gens_for_inverse_bayes as alloc_f

#State the objective function, its arguments, output, and necessary parameters (and their sizes)
sim_specs = {'sim_f': sim_f, # This is the function whose output is being minimized
             'in': ['x'], # These keys will be given to the above function
             'out': [('like',float), # This is the output from the function being minimized
                    ],
             }

# State the generating function, its arguments, output, and necessary parameters.
gen_specs = {'gen_f': gen_f,
             'in': [],
             'out': [('x',float,2),('batch',int),('subbatch',int),('prior',float,1),('prop',float,1), ('weight',float,1)],
             'lb': np.array([-3,-2]),
             'ub': np.array([ 3, 2]),
             'subbatch_size': 3,
             'num_subbatches': 2,
             'num_batches': 10,
             }

# Tell libEnsemble when to stop
exit_criteria = {'sim_max': gen_specs['subbatch_size']*gen_specs['num_subbatches']*gen_specs['num_batches'], 'elapsed_wallclock_time': 300}

np.random.seed(1)
persis_info = {}
for i in range(1,nworkers+1):
    persis_info[i] = {'rand_stream': np.random.RandomState(i)}

alloc_specs = {'out':[], 'alloc_f':alloc_f}

if nworkers < 2:
    # Can't do a "persistent worker run" if only one worker
    quit()

# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs, libE_specs)


if is_master:
    assert flag == 0
    # Change the last weights to correct values (H is a list on other cores and only array on manager)
    ind = 2*gen_specs['subbatch_size']*gen_specs['num_subbatches']
    H[-ind:] = H['prior'][-ind:] + H['like'][-ind:] - H['prop'][-ind:]
    # np.save('in_bayes_ex', H)
    assert len(H) == 60, "Failed"
