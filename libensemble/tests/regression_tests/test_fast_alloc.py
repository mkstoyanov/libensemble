# """
# Runs libEnsemble on the 6-hump camel problem. Documented here:
#    https://www.sfu.ca/~ssurjano/camel6.html
#
# Execute via the following command:
#    mpiexec -np 4 python3 call_6-hump_camel.py
# The number of concurrent evaluations of the objective function will be 4-1=3.
# """

from __future__ import division
from __future__ import absolute_import

import numpy as np

# Import libEnsemble main, sim_specs, gen_specs, alloc_specs, and persis_info
from libensemble.libE import libE
from libensemble.tests.regression_tests.support import six_hump_camel_simple_sim_specs as sim_specs
from libensemble.tests.regression_tests.support import uniform_random_sample_gen_specs as gen_specs
from libensemble.tests.regression_tests.support import give_sim_work_first_alloc_specs as alloc_specs
from libensemble.tests.regression_tests.support import persis_info_0 as persis_info

from libensemble.tests.regression_tests.common import parse_args
nworkers, is_master, libE_specs, _ = parse_args()
# State the generating function, its arguments, output, and necessary parameters.
num_pts = 30*(nworker-1)
gen_specs['gen_batch_size'] = num_pts
gen_specs['num_active_gens'] = 1
gen_specs['out'] = [('x',float,(2,))]
gen_specs['lb'] = np.array([-3,-2])
gen_specs['ub'] = np.array([ 3, 2])

from libensemble.tests.regression_tests.common import parse_args

# Parse args for test code
_, is_master, libE_specs, _ = parse_args()
if libE_specs['comms'] == 'tcp':
    # Can't use the same interface for manager and worker if we want
    # repeated calls to libE -- the manager sets up a different server
    # each time, and the worker will not know what port to connect to.
    quit()

for time in np.append([0], np.logspace(-5,-1,5)):
    for rep in range(1):
        #State the objective function, its arguments, output, and necessary parameters (and their sizes)
        sim_specs['pause_time'] = time

        if time == 0:
            sim_specs.pop('pause_time')
            gen_specs['gen_batch_size'] = num_pts//2

        # Tell libEnsemble when to stop
        exit_criteria = {'sim_max': num_pts, 'elapsed_wallclock_time': 300}

        persis_info['next_to_give'] = 0
        persis_info['total_gen_calls'] = 1

        H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs, libE_specs)

        if is_master:
            assert flag == 0
            assert len(H) == num_pts
