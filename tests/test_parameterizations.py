import unittest

import numpy as np
import autograd.numpy as npa
import scipy.sparse as sp
import scipy.sparse.linalg as spl
import copy

from autograd.extend import primitive, defvjp
from autograd import grad

from ceviche.utils import grad_num
from ceviche.primitives import *
from ceviche.fdfd import fdfd_hz, fdfd_ez

"""
This file tests the autograd gradients of an FDFD and makes sure that they
equal the numerical derivatives
"""

# test parameters
ALLOWED_RATIO = 1e-4    # maximum allowed ratio of || grad_num - grad_auto || vs. || grad_num ||
VERBOSE = False         # print out full gradients?
DEPS = 1e-6             # numerical gradient step size

class TestFDFD(unittest.TestCase):

    """ Tests the flexible objective function specifier """

    def setUp(self):

        # basic simulation parameters
        self.Nx = 30
        self.Ny = 30
        self.omega = 2*np.pi*200e12
        self.dL = 1e-6
        self.pml = [5, 5]

        self.source_mask = np.ones((self.Nx, self.Ny))
        self.source_mask[5, 5] = 1

        # sources (chosen to have objectives around 1)
        self.source_amp = 1e-8

        self.source = np.zeros((self.Nx, self.Ny))
        self.source[self.Nx//2, self.Ny//2] = self.source_amp

        # background relative permittivity
        self.eps_r   = np.zeros((self.Nx, self.Ny))
        self.eps_arr = self.eps_r.flatten()

    def check_gradient_error(self, grad_num, grad_auto):
        """ Checks the test case:
            compares the norm of the gradient to the norm of the difference
            Throws error if this is greater than ALLOWED RATIO
        """
        norm_grad = np.linalg.norm(grad_num)
        print('\t\tnorm of gradient:   ', norm_grad)
        norm_diff = np.linalg.norm(grad_num - grad_auto)
        print('\t\tnorm of difference: ', norm_diff)
        norm_ratio = norm_diff / norm_grad        
        print('\t\tratio of norms:     ', norm_ratio)
        self.assertLessEqual(norm_ratio, ALLOWED_RATIO)
        print('')

    def template_continuous(self, param):
        """ Template for testing a continuous parameterization `param`"""

        print('\ttesting {} parameterization'.format(param))

        # define where to perturb gradient
        design_region = np.zeros((self.Nx, self.Ny))
        design_region[self.Nx//4:self.Nx*3//4, self.Ny//4:self.Ny*3//4] = 1

        # other parameters
        eps_max = 5

        # initialize the parameters
        init_params = np.random.random((self.Nx * self.Ny,))

        # set the starting epsilon using the parameterization
        eps_init = param.get_eps(init_params, self.eps_r, design_region, eps_max)

        # initialize FDFD with this permittivity
        f = fdfd_hz(self.omega, self.dL, eps_init, self.pml)

        def objective(params):

            # get the permittivity for this set of parameters
            eps_new = param.get_eps(params, eps_init, design_region, eps_max)

            # set the permittivity
            f.eps_r = eps_new

            # set the source amplitude to the permittivity at that point
            Ex, Ey, Hz = f.solve(eps_new * self.source)

            return npa.sum(npa.square(npa.abs(Hz))) \
                 + npa.sum(npa.square(npa.abs(Ex))) \
                 + npa.sum(npa.square(npa.abs(Ey)))

        grad_autograd = grad(objective)(init_params)
        grad_numerical = grad_num(objective, init_params, step_size=DEPS)

        if VERBOSE:
            print('\tobjective function value: ', objective(init_params))
            print('\tgrad (auto):  \n\t\t', grad_autograd)
            print('\tgrad (num):   \n\t\t\n', grad_numerical)

        self.check_gradient_error(grad_numerical, grad_autograd)


    def test_continuous(self):
        """ Test all continuous parmaterization functions """

        from ceviche.parameterizations import Param_Topology

        test_params = [Param_Topology]
        for param in test_params:
            self.template_continuous(param)



if __name__ == '__main__':
    unittest.main()