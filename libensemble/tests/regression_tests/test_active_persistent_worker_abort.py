# """
# Runs libEnsemble on the 6-hump camel problem. Documented here:
#    https://www.sfu.ca/~ssurjano/camel6.html
#
# Execute via one of the following commands (e.g. 3 workers):
#    mpiexec -np 4 python3 test_6-hump_camel_active_persistent_worker_abort.py
#    python3 test_6-hump_camel_active_persistent_worker_abort.py --nworkers 3 --comms local
#    python3 test_6-hump_camel_active_persistent_worker_abort.py --nworkers 3 --comms tcp
#
# The number of concurrent evaluations of the objective function will be 4-1=3.
# """

# Do not change these lines - they are parsed by run-tests.sh
# TESTSUITE_COMMS: mpi local tcp
# TESTSUITE_NPROCS: 3 4

import sys
import numpy as np

# Import libEnsemble requirements
from libensemble.libE import libE
from libensemble.sim_funcs.six_hump_camel import six_hump_camel as sim_f
from libensemble.gen_funcs.uniform_or_localopt import uniform_or_localopt as gen_f
from libensemble.alloc_funcs.start_persistent_local_opt_gens import start_persistent_local_opt_gens as alloc_f
from libensemble.tools import parse_args, save_libE_output, add_unique_random_streams
from libensemble.tests.regression_tests.support import uniform_or_localopt_gen_out as gen_out

nworkers, is_manager, libE_specs, _ = parse_args()

sim_specs = {'sim_f': sim_f, 'in': ['x'], 'out': [('f', float)]}

gen_out += [('x', float, 2), ('x_on_cube', float, 2)]
gen_specs = {'gen_f': gen_f,
             'persis_in': ['x', 'f'],
             'out': gen_out,
             'user': {'localopt_method': 'LN_BOBYQA',
                      'xtol_rel': 1e-4,
                      'lb': np.array([-3, -2]),
                      'ub': np.array([3, 2]),
                      'gen_batch_size': 2,
                      'dist_to_bound_multiple': 0.5,
                      'localopt_maxeval': 4
                      }
             }

alloc_specs = {'alloc_f': alloc_f, 'out': gen_out, 'user': {'batch_mode': True, 'num_active_gens': 1}}

persis_info = add_unique_random_streams({}, nworkers + 1)

# Set sim_max small so persistent worker is quickly terminated
exit_criteria = {'sim_max': 10, 'elapsed_wallclock_time': 300}

if nworkers < 2:
    sys.exit("Cannot run with a persistent worker if only one worker -- aborting...")

# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info,
                            alloc_specs, libE_specs)

if is_manager:
    assert flag == 0
    save_libE_output(H, persis_info, __file__, nworkers)
