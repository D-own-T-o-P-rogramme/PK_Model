#
# Solution class
#
import numpy as np
import matplotlib.pyplot as plt
import scipy.integrate


class Solution:
    """A Pharmokinetic (PK) model solution

    Parameters
    ----------

    value: numeric, optional
        an example paramter

    model: using model class
        with model( Vc, Vps, Qps, CL)

    protocol: using protocoll class to specify
        intravenous or subcutaneous dosing

    tmax: float
        integrates until it reaches tmax
        default value is 1

    nsteps: int
        number of integration steps
        default value is 1000

    """
    def __init__(self, model, protocol, tmax=1, nsteps=1000):
        self.model = model
        self.protocol = protocol
        self.t_eval = np.linspace(0, tmax, nsteps)
        self.solver()

    def rhs_intravenous(self, t, y):
        '''
        Right hand side of flux equation
        dimension of system = number of compartments = self.model.size
        Parameters
        ----------
        t: time
        y: state vector [qc, q_p1, q_p2]
        '''
        state = y
        Vc = self.model.Vc  # volume of the main compartment
        CL = self.model.CL  # Clearance rate
        cleared = state[0] / Vc * CL  # flux going out of the main compartment
        dq_dt = [0]  # [dqc, dq_p1, dq_p2]

        flux_sum = 0  # sum of flux between compartments
        # loop over peripheral compartments
        for comp in range(1, self.model.size):
            # transition rate etween main compartment
            # and i-th peripheral compartment
            Q_pi = self.model.Qps[comp - 1]
            # volume of i-th peripheral compartment
            V_pi = self.model.Vps[comp - 1]
            # flux between peripheral and main compartment
            flux = Q_pi * (state[0] / Vc - state[comp] / V_pi)
            dq_dt.append(flux)
            flux_sum += flux
        dq_dt[0] = self.protocol.dose_time_function(t) - cleared - flux_sum
        return dq_dt

    def rhs_subcutaneous(self, t, y):  # subcutaneous
        state = y   # one dim more than intravenous
        Vc = self.model.Vc
        CL = self.model.CL
        cleared = state[1] / Vc * CL
        dq_dt = [0, 0]  # [dq0, dqc, dq_p1, dq_p2]
        dq0_dt = self.protocol.dose_time_function(t)
        dq0_dt -= self.protocol.k_a * state[0]
        dq_dt[0] = dq0_dt
        flux_sum = 0
        # loop over peripheral compartments
        for comp in range(1, self.model.size):
            Q_pi = self.model.Qps[comp - 1]
            V_pi = self.model.Vps[comp - 1]
            flux = Q_pi * (state[1] / Vc - state[comp + 1] / V_pi)
            dq_dt.append(flux)
            flux_sum += flux
        dq_dt[1] = self.protocol.k_a * state[0] - cleared - flux_sum
        return dq_dt

    def solver(self):
        if self.protocol.subcutaneous:
            step_func = self.rhs_subcutaneous
            self.y0 = np.zeros(self.model.size + 1)
            self.sol = np.zeros(self.model.size + 1)
        else:
            step_func = self.rhs_intravenous
            # only central compartment n=1, one periphal comartment n=2
            # two periphal compartment n=3
            self.y0 = np.zeros(self.model.size)
            self.sol = np.zeros(self.model.size)

        sol = scipy.integrate.solve_ivp(
            fun=lambda t, y: step_func(t, y),
            t_span=[self.t_eval[0], self.t_eval[-1]],
            y0=self.y0, t_eval=self.t_eval
        )
        self.sol = sol
        return sol

    def generate_plot(self, separate=False):
        """
        Generate a plot of the drug quantity per
        compartment over time for the corresponding model

        :param separate: set to True if you want 1 plot per compartment
        :returns: matplotlib figure
        """
        sol = self.solver()
        n = self.model.size
        if separate:
            fig = plt.figure(figsize=(n * 4.0, 3.0))
            central = fig.add_subplot(1, n, 1)
            central.plot(sol.t, sol.y[0, :], label='- q_c')
            central.legend()
            central.set_title('Central compartment')
        else:
            fig = plt.figure()
            plt.plot(sol.t, sol.y[0, :], label='- q_c')

        # add legend and axes labels
        plt.ylabel('drug mass [ng]')
        plt.xlabel('time [h]')

        # loop over peripheral compartments and plot drug quantity for each
        for i in range(n - 1):
            label = '- q_p' + str(i + 2)
            if separate:
                subplot = fig.add_subplot(1, n, i + 2)
                subplot.plot(sol.t, sol.y[i + 1, :], label=label)
                subplot.legend()
                subplot.set_xlabel('time [h]')
                subplot.set_title('Peripheral compartment #' + str(i + 1))
            else:
                plt.plot(sol.t, sol.y[i + 1, :], label=label)
        plt.legend()
        fig.tight_layout()
        plt.show()
        return fig
