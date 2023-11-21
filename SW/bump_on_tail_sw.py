import sys, os

sys.path.append(os.path.abspath(os.path.join('..')))
import numpy as np
from operators.SW_sqrt import RHS
from operators.SW import solve_poisson_equation_two_stream
from operators.SW import integral_I0, integral_I1
from FD_tools.finite_difference_operators import ddx_central
from FD_tools.implicit_midpoint import implicit_midpoint_solver


def rhs(y, t):
    dydt_ = np.zeros(len(y))

    # initialize the states
    state_e1 = np.zeros((Nv, Nx - 1))
    state_e2 = np.zeros((Nv, Nx - 1))
    state_i = np.zeros((Nv, Nx - 1))
    # static/background ions
    state_i[0, :] = (1 / (np.sqrt(2 * np.sqrt(np.pi)))) * np.ones(Nx - 1) / alpha_i

    for jj in range(Nv):
        state_e1[jj, :] = y[jj * (Nx - 1): (jj + 1) * (Nx - 1)]
        state_e2[jj, :] = y[Nv * (Nx - 1) + jj * (Nx - 1): Nv * (Nx - 1) + (jj + 1) * (Nx - 1)]

    E = solve_poisson_equation_two_stream(state_e1=state_e1,
                                          state_e2=state_e2,
                                          state_i=state_i,
                                          alpha_e1=alpha_e1,
                                          alpha_e2=alpha_e2,
                                          alpha_i=alpha_i,
                                          dx=dx,
                                          Nx=Nx-1,
                                          Nv=Nv,
                                          solver="gmres",
                                          order_fd=2,
                                          L=L)

    for jj in range(Nv):
        dydt_[jj * (Nx - 1): (jj + 1) * (Nx - 1)] = RHS(state=state_e1,
                                                        m=jj,
                                                        Nv=Nv,
                                                        alpha_s=alpha_e1,
                                                        q_s=q_e1,
                                                        dx=dx,
                                                        Nx=Nx,
                                                        m_s=m_e1,
                                                        E=E,
                                                        u_s=u_e1)

        dydt_[Nv * (Nx - 1) + jj * (Nx - 1): Nv * (Nx - 1) + (jj + 1) * (Nx - 1)] = RHS(state=state_e2,
                                                                                        m=jj,
                                                                                        Nv=Nv,
                                                                                        alpha_s=alpha_e2,
                                                                                        q_s=q_e2,
                                                                                        dx=dx,
                                                                                        Nx=Nx,
                                                                                        m_s=m_e2,
                                                                                        E=E,
                                                                                        u_s=u_e2)

    # mass drift (even)
    dydt_[-1] = -dx * (q_e1 / m_e1) * np.sqrt((Nv - 1) / 2) * integral_I0(n=Nv - 2) * E.T @ state_e1[-1, :] \
               - dx * (q_e2 / m_e2) * np.sqrt((Nv - 1) / 2) * integral_I0(n=Nv - 2) * E.T @ state_e2[-1, :] \
               - dx * (q_i / m_i) * np.sqrt((Nv - 1) / 2) * integral_I0(n=Nv - 2) * E.T @ state_i[-1, :]

    # momentum drift (odd)
    dydt_[-2] = -dx * (Nv - 1) * integral_I0(n=Nv - 1) * E.T @ (alpha_e1 * q_e1 * state_e1[-1, :] +
                                                                alpha_e2 * q_e2 * state_e2[-1, :] +
                                                                alpha_i * q_i * state_i[-1, :])
    # momentum (even)
    dydt_[-3] = -dx * np.sqrt((Nv - 1) / 2) * integral_I0(n=Nv - 2) * E.T @ (u_e1 * q_e1 * state_e1[-1, :] +
                                                                             u_e2 * q_e2 * state_e2[-1, :] +
                                                                             u_i * q_i * state_i[-1, :])

    # energy drift (odd)
    dydt_[-4] = -dx * (Nv - 1) * integral_I0(n=Nv - 1) * E.T @ (u_e1 * q_e1 * state_e1[-1, :] +
                                                                u_e2 * q_e2 * state_e2[-1, :] +
                                                                u_i * q_i * state_i[-1, :])
    # energy drift (even)
    D = ddx_central(Nx=Nx, dx=dx)
    D_pinv = np.linalg.pinv(D)
    dydt_[-5] = -dx * np.sqrt((Nv - 1) / 2) * integral_I0(n=Nv - 2) * E.T @ (
                 q_e1 * ((2 * Nv - 1) * (alpha_e1 ** 2) + u_e1 ** 2) * state_e1[-1, :]
               + q_e2 * ((2 * Nv - 1) * (alpha_e2 ** 2) + u_e2 ** 2) * state_e2[-1, :]
               + q_i * ((2 * Nv - 1) * (alpha_i ** 2) + u_i ** 2) * state_i[-1, :]
               + q_e1**2/m_e1 * D_pinv @ (E * state_e1[-1, :])
               + q_e2**2/m_e2 * D_pinv @ (E * state_e2[-1, :])
               + q_i**2/m_i * D_pinv @ (E * state_i[-1, :]))

    return dydt_


if __name__ == '__main__':
    # set up configuration parameters
    # number of mesh points in x
    Nx = 101
    # number of spectral expansions
    Nv = 101
    # epsilon displacement in initial electron distribution
    epsilon = 0.03
    # velocity scaling of electron and ion
    alpha_e1 = 1
    alpha_e2 = 1 / 2
    alpha_i = np.sqrt(1 / 1863)
    # x grid is from 0 to L
    L = 20 * np.pi
    # spacial spacing dx = x[i+1] - x[i]
    dx = L / (Nx - 1)
    # time stepping
    dt = 1e-2
    # final time
    T = 15
    t_vec = np.linspace(0, T, int(T / dt) + 1)
    # total number of time stepping
    Nt = int(T / dt)
    # velocity scaling
    u_e1 = 0
    u_e2 = 4.5
    u_i = 0
    # mass normalized
    m_e1 = 1
    m_e2 = 1
    m_i = 1863
    # charge normalized
    q_e1 = -1
    q_e2 = -1
    q_i = 1
    # delta for initial condition
    delta1 = 9 / 10
    delta2 = 1 / 10

    # spatial grid
    x = np.linspace(0, L, Nx)

    # initial condition of the first expansion coefficient
    C_0e1 = delta1 * (1 / (np.sqrt(2 * np.sqrt(np.pi)))) * (1 + epsilon * np.cos(0.3 * x)) / alpha_e1
    C_0e2 = delta2 * (1 / (np.sqrt(2 * np.sqrt(np.pi)))) * (1 + epsilon * np.cos(0.3 * x)) / alpha_e2
    C_0i = (1 / (np.sqrt(2 * np.sqrt(np.pi)))) * np.ones(Nx) / alpha_i

    # initialize states (electrons type 1 and 2)
    states_e1 = np.zeros((Nv, Nx - 1, Nt))
    states_e2 = np.zeros((Nv, Nx - 1, Nt))
    states_i = np.zeros((Nv, Nx - 1, Nt))

    # initialize the expansion coefficients
    states_e1[0, :, 0] = C_0e1[:-1]
    states_e2[0, :, 0] = C_0e2[:-1]
    states_i[0, :, 0] = C_0i[:-1]

    # initial condition of the semi-discretized ODE
    y0 = np.zeros((2 * Nv) * (Nx - 1) + 5)
    y0[:(Nx - 1) * Nv] = states_e1[:, :, 0].flatten("C")
    y0[Nv * (Nx - 1): 2 * Nv * (Nx - 1)] = states_e2[:, :, 0].flatten("C")

    # integrate (symplectic integrator: implicit midpoint)
    sol_midpoint_u = implicit_midpoint_solver(t_vec=t_vec, y0=y0, rhs=rhs, nonlinear_solver_type="newton_krylov",
                                              r_tol=1e-8, a_tol=1e-14, max_iter=100)

    np.save("../data/SW/bump_on_tail/poisson/sol_midpoint_u_101", sol_midpoint_u)
    np.save("../data/SW/bump_on_tail/poisson/sol_midpoint_t_101", t_vec)