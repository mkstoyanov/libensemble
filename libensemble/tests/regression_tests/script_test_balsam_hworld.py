# This script is submitted as an app and job to Balsam. The job submission is
#   via 'balsam launch' executed in the test_balsam_hworld.py script.

import numpy as np
import mpi4py
from mpi4py import MPI

from libensemble.executors.balsam_executor import BalsamMPIExecutor
from libensemble.message_numbers import WORKER_DONE, WORKER_KILL_ON_ERR, WORKER_KILL_ON_TIMEOUT, TASK_FAILED
from libensemble.libE import libE
from libensemble.sim_funcs.executor_hworld import executor_hworld
from libensemble.gen_funcs.sampling import uniform_random_sample
from libensemble.tools import add_unique_random_streams
import libensemble.sim_funcs.six_hump_camel as six_hump_camel

mpi4py.rc.recv_mprobe = False  # Disable matching probes

libE_specs = {'mpi_comm': MPI.COMM_WORLD,
              'comms': 'mpi',
              'save_every_k_sims': 400,
              'save_every_k_gens': 20,
              }

nworkers = MPI.COMM_WORLD.Get_size() - 1
is_manager = MPI.COMM_WORLD.Get_rank() == 0

cores_per_task = 1

sim_app = './my_simtask.x'
sim_app2 = six_hump_camel.__file__

exctr = BalsamMPIExecutor(auto_resources=False, central_mode=False, custom_info={'not': 'used'})
exctr.register_calc(full_path=sim_app, calc_type='sim')  # Default 'sim' app - backward compatible
exctr.register_calc(full_path=sim_app2, app_name='six_hump_camel')  # Named app

sim_specs = {'sim_f': executor_hworld,
             'in': ['x'],
             'out': [('f', float), ('cstat', int)],
             'user': {'cores': cores_per_task,
                      'balsam_test': True}
             }

gen_specs = {'gen_f': uniform_random_sample,
             'in': ['sim_id'],
             'out': [('x', float, (2,))],
             'user': {'lb': np.array([-3, -2]),
                      'ub': np.array([3, 2]),
                      'gen_batch_size': nworkers}
             }

persis_info = add_unique_random_streams({}, nworkers + 1)

exit_criteria = {'elapsed_wallclock_time': 60}

# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria,
                            persis_info, libE_specs=libE_specs)

if is_manager:
    print('\nChecking expected task status against Workers ...\n')
    calc_status_list_in = np.asarray([WORKER_DONE, WORKER_KILL_ON_ERR,
                                      WORKER_DONE, WORKER_KILL_ON_TIMEOUT,
                                      TASK_FAILED, 0])
    calc_status_list = np.repeat(calc_status_list_in, nworkers)

    print("Expecting: {}".format(calc_status_list))
    print("Received:  {}\n".format(H['cstat']))

    assert np.array_equal(H['cstat'], calc_status_list), "Error - unexpected calc status. Received: " + str(H['cstat'])

    # Check summary file:
    print('Checking expected task status against task summary file ...\n')

    calc_desc_list_in = ['Completed', 'Worker killed task on Error', 'Completed',
                         'Worker killed task on Timeout', 'Task Failed',
                         'Manager killed on finish']

    # Repeat N times for N workers and insert Completed at start for generator
    calc_desc_list = ['Completed'] + calc_desc_list_in*nworkers

    # Cleanup (maybe cover del_apps() and del_tasks())
    exctr.del_apps()
    exctr.del_tasks()

    print("\n\n\nRun completed.")
