#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@author:qzz
@file:Jacks_car_rental.py
@time:2021/12/10
"""
import gym
import numpy as np
import scipy.stats

import mdp


class JacksCarRental(mdp.MDP):
    gamma = 0.9
    max_cars = 20
    max_poisson = 15
    max_transfer = 5

    rental_price = 10
    transfer_cost = 2

    # 1-5:2->1 6-10:1->2
    action_space = gym.spaces.Discrete(2 * max_transfer + 1)

    observation_space = gym.spaces.MultiDiscrete([max_cars + 1, max_cars + 1])
    reward_range = (-transfer_cost * max_transfer, rental_price * max_cars * 2)
    metadata = {'render.modes': ['ansi']}

    def __init__(self, max_poisson=None):
        max_poisson = max_poisson if max_poisson else self.max_poisson

        n_requests_returns = np.indices([max_poisson] * 4).reshape([4, -1]).T
        self.n_requests = n_requests_returns[:, :2]
        self.n_returns = n_requests_returns[:, 2:]
        assert (0 <= self.n_returns).all() and (self.n_returns <= max_poisson).all()
        assert (0 <= self.n_requests).all() and (self.n_requests <= max_poisson).all()

        requests_lambda = np.array([3, 4])
        returns_lambda = np.array([3, 2])
        dist_requests = scipy.stats.poisson(requests_lambda)
        dist_returns = scipy.stats.poisson(returns_lambda)
        p_requests = dist_requests.pmf(self.n_requests)
        p_returns = dist_returns.pmf(self.n_returns)
        self.ps = np.prod(p_requests * p_returns, axis=1)
        assert (0 < self.ps).all() and (self.ps < 1).all()
        self.ps /= np.sum(self.ps)

        self.reset()

    def reset(self):
        self.state = np.random.randint(0, self.max_cars, size=2)

    def transitions(self, state, action):
        assert self.action_space.contains(action)
        assert self.observation_space.contains(state)

        # transfer at night
        transfer = action - self.max_transfer
        transfer_cost = self.transfer_cost * abs(transfer)
        if transfer > 0:
            transferred = min(abs(transfer), state[0])
            transferred = min(transferred, self.max_cars - state[1])
        else:
            transferred = min(abs(transfer), state[1])
            transferred = -min(transferred, self.max_cars - state[0])

        transitions = state + np.array([-transferred, transferred])
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # rent
        n_rented = np.minimum(self.n_requests, transitions)
        transitions = transitions - n_rented
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # return
        n_returned = np.minimum(self.n_returns, self.max_cars - transitions)
        transitions = transitions + n_returned
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # reward
        rental_revenue = self.rental_price * np.sum(n_rented, axis=1)
        rewards = rental_revenue - transfer_cost
        assert (self.reward_range[0] <= rewards).all() and (rewards <= self.reward_range[1]).all()

        # probability
        ps = self.ps

        # terminals
        terminals = np.zeros_like(rewards, dtype=np.bool)

        return transitions, rewards, ps, terminals


class NonlinearJacksCarRental(JacksCarRental):
    max_parked = 10
    parked_cost = 4
    reward_range = (JacksCarRental.reward_range[0] - 2 * parked_cost, JacksCarRental.reward_range[1])

    def transitions(self, state, action):
        assert self.action_space.contains(action)
        assert self.observation_space.contains(state)

        # transfer at night
        transfer = action - self.max_transfer
        transfer_cost = self.transfer_cost * abs(transfer)
        if transfer > 0:
            transferred = min(abs(transfer), state[0])
            transferred = +min(transferred, self.max_cars - state[1])
            transfer_cost -= 2
        else:
            transferred = min(abs(transfer), state[1])
            transferred = -min(transferred, self.max_cars - state[0])

        transitions = state + np.array([-transferred, +transferred])
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # parking cost
        parked_cost = self.parked_cost * np.sum((self.max_parked < transitions))

        # rent
        n_rented = np.minimum(self.n_requests, transitions)
        transitions = transitions - n_rented
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # return
        n_returned = np.minimum(self.n_returns, self.max_cars - transitions)
        transitions = transitions + n_returned
        assert (0 <= transitions).all() and (transitions <= self.max_cars).all()

        # reward
        rental_revenue = self.rental_price * np.sum(n_rented, axis=1)
        rewards = rental_revenue - parked_cost - transfer_cost
        assert (self.reward_range[0] <= rewards).all() and (rewards <= self.reward_range[1]).all()

        # probability
        ps = self.ps

        # Flag for terminal transitions (there are none)
        terminals = np.zeros_like(rewards, dtype=np.bool)

        return transitions, rewards, ps, terminals
