#if yoyu didn't want to make alloc_support a class (and maybe you do), but if you didn'tyou could hold the reosurce cache in the schedular - if you create it each time.
#perhaps this should go under resources directory? Out of user space - but as class they could inherit to change.
import copy
import numpy as np
from libensemble.resources.resources import Resources  # SH TODO: Consider alt - passing resources via libE_info to alloc_func.

class ResourceSchedulerException(Exception):
    "Raised for any exception in the alloc support"


class ResourceScheduler:

    def __init__(self, user_resources=None):
        self.resources = user_resources or Resources.resources.managerworker_resources
        self.avail_rsets_by_group = None  #could set here - but might save time not doing so if not used.

    def assign_resources(self, rsets_req):
        """Schedule resource sets to a work item if possible and assign to worker

        If the resources required are less than one node, they will be
        allocated to the smallest available sufficient slot.

        If the resources required are more than one node, then enough
        full nodes will be allocated to cover the requirement.

        The assigned resources are marked directly in the resources module.

        Returns a list of resource sets ids. A return of None implies
        insufficient resources.
        """

        if rsets_req > self.resources.num_rsets:
            # Raise error - when added errors
            raise ResourceSchedulerException("More resource sets requested {} than exist {}" \
                .format(rsets_req, self.resources.num_rsets))

        # Quick check
        #print('free', self.resources.rsets_free)
        if rsets_req > self.resources.rsets_free:
            return None

        num_groups = self.resources.num_groups
        max_grpsize = self.resources.rsets_per_node  #assumes even

        #when use class will do this once for an alloc call!
        avail_rsets_by_group = self.get_avail_rsets_by_group()
        print('avail_rsets_by_group before', self.avail_rsets_by_group)

        #Maybe more efficient way than making copy_back
        tmp_avail_rsets_by_group = copy.deepcopy(avail_rsets_by_group)

        # print('Available rsets_by_group:', avail_rsets_by_group)  # SH TODO: Remove

        print('max_grpsize is', max_grpsize)
        if max_grpsize is not None:
            max_upper_bound = max_grpsize + 1
        else:
            # All in group zero
            # Will still block workers, but treats all as one group
            if len(tmp_avail_rsets_by_group) > 1:
                raise AllocException("There should only be one group if resources is not set")
            max_upper_bound = len(tmp_avail_rsets_by_group[0]) + 1

        # SH TODO: Review scheduling > 1 node strategy
        # Currently tries for even split and if cannot, then rounds rset up to full nodes.
        # Log if change requested to make fit/round up - at least at debug level.
        if self.resources.even_groups:
            rsets_req, num_groups_req, rsets_req_per_group = self.calc_rsets_even_grps(rsets_req, max_grpsize, num_groups)
        else:
            print('Warning: uneven groups - but using even groups function')
            rsets_req, num_groups_req, rsets_req_per_group = self.calc_rsets_even_grps(rsets_req, max_grpsize, num_groups)

        # Now find slots on as many nodes as need
        accum_team = []
        group_list = []
        print('\nLooking for {} rsets'.format(rsets_req))
        for ng in range(num_groups_req):
            print(' - Looking for group {} out of {}: Groupsize {}'.format(ng+1, num_groups_req, rsets_req_per_group))
            cand_team = []
            cand_group = None
            upper_bound = max_upper_bound
            for g in tmp_avail_rsets_by_group:
                print('   -- Search possible group {} in {}'.format(g, tmp_avail_rsets_by_group))

                if g in group_list:
                    continue
                nslots = len(tmp_avail_rsets_by_group[g])
                if nslots == rsets_req_per_group:  # Exact fit.  # If make array - could work with different sized group requirements.
                    cand_team = tmp_avail_rsets_by_group[g].copy()  # SH TODO: check do I still need copy - given extend below?
                    cand_group = g
                    break  # break out inner loop...
                elif rsets_req_per_group < nslots < upper_bound:
                    cand_team = tmp_avail_rsets_by_group[g][:rsets_req_per_group]
                    cand_group = g
                    upper_bound = nslots
            if cand_group is not None:
                accum_team.extend(cand_team)
                group_list.append(cand_group)

                print('      here b4:  group {} avail {} - cand_team {}'.format(group_list, tmp_avail_rsets_by_group, cand_team))
                #import pdb;pdb.set_trace()
                for rset in cand_team:
                    tmp_avail_rsets_by_group[cand_group].remove(rset)
                print('      here aft: group {} avail {}'.format(group_list, tmp_avail_rsets_by_group))

        print('Found rset team {} - group_list {}'.format(accum_team, group_list))
        #import pdb;pdb.set_trace()

        if len(accum_team) == rsets_req:
            # A successful team found
            rset_team = sorted(accum_team)
            print('Setting rset team {} - group_list {}'.format(accum_team, group_list))
            self.avail_rsets_by_group = tmp_avail_rsets_by_group #maybe use function to update
            print('avail_rsets_by_group after', self.avail_rsets_by_group)
        else:
            rset_team = None  # Insufficient resources to honor

        # print('Assigned rset team {} to worker {}'.format(rset_team,worker_id))  # SH TODO: Remove

        #SH TODO: As move to class this will be packed and a temporary buffer used in the alloc so that
        #work units can be cancelled - ie manager always assigns actual resources when sending out.
        #self.resources.assign_rsets(rset_team, worker_id)

        #print("rsets assigned",self.resources.rsets['assigned'])

        return rset_team


    # Also could follow my other approaches and make static and pass resources (can help with testing)
    # SH TODO: An alt. could be to return an object
    #          When merge CWP branch - will need option to use active receive worker
    def get_avail_rsets_by_group(self):
        """Return a dictionary of resource set IDs for each group (e.g. node)

        If groups are not set they will all be in one group (group 0)

        E.g: Say 8 resource sets / 2 nodes
        GROUP  1: [1,2,3,4]
        GROUP  2: [5,6,7,8]
        """
        if self.avail_rsets_by_group is None:
            rsets = self.resources.rsets
            groups = np.unique(rsets['group'])
            self.avail_rsets_by_group = {}
            for g in groups:
                self.avail_rsets_by_group[g] = []
            for ind, rset in enumerate(rsets):
                if not rset['assigned']:
                    g = rset['group']
                    self.avail_rsets_by_group[g].append(ind)
        return self.avail_rsets_by_group


    #This could be inherited/overidden for uneven etc.....
    #that would be good reason not to be static (though could be class method).
    #in which case prob just call calc_rsets_grps or something even better!!
    def calc_rsets_even_grps(self, rsets_req, max_grpsize, max_groups):
        """Calculate an even breakdown to best fit rsets_req input"""

        num_groups_req = rsets_req//max_grpsize + (rsets_req % max_grpsize > 0)  # Divide with roundup.

        # Up to max groups - keep trying for an even split
        if num_groups_req > 1:
            even_partition = False
            tmp_num_groups = num_groups_req
            while tmp_num_groups <= max_groups:
                if rsets_req % tmp_num_groups == 0:
                    even_partition = True
                    break
                tmp_num_groups += 1

            if even_partition:
                num_groups_req = tmp_num_groups
                rsets_req_per_group = rsets_req//num_groups_req  # This should always divide perfectly.
            else:
                #log here
                print('Warning: Increasing resource requirement to obtain an even partition of resource sets to nodes')
                rsets_req_per_group = rsets_req//num_groups_req + (rsets_req % num_groups_req > 0)
                rsets_req = num_groups_req * rsets_req_per_group
        else:
            rsets_req_per_group = rsets_req

        return rsets_req, num_groups_req, rsets_req_per_group


class UnevenResourceScheduler(ResourceScheduler):

    def assign_resources(rsets_req, worker_id, user_resources=None):
        pass



