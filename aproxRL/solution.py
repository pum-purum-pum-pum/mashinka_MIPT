# -*- coding: utf-8 -*-
import gym
import math
import random
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from collections import namedtuple
from itertools import count
from copy import deepcopy
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable
import torchvision.transforms as T
%matplotlib inline

env = gym.make('LunarLander-v2')

# set up matplotlib
is_ipython = 'inline' in matplotlib.get_backend()
if is_ipython:
    from IPython import display

plt.ion()

# if gpu is to be used
use_cuda = torch.cuda.is_available()
FloatTensor = torch.cuda.FloatTensor if use_cuda else torch.FloatTensor
LongTensor = torch.cuda.LongTensor if use_cuda else torch.LongTensor
ByteTensor = torch.cuda.ByteTensor if use_cuda else torch.ByteTensor
Tensor = FloatTensor

# %%

Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))


class ReplayMemory(object):

    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0

    def push(self, *args):
        """Saves a transition."""
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)

class DQN(nn.Module):
    def __init__(self, action_n):
        super(DQN, self).__init__()
        self.out_size = action_n
        hidden_size = 8
        self.dense1 = nn.Linear(8, hidden_size)
        self.nl1 = nn.Sigmoid()
        self.dense2 = nn.Linear(hidden_size, self.out_size)
        self.sm = nn.Softmax()

    def forward(self, x):
        out = self.dense1(x)
        out = self.nl1(out)
        out = self.dense2(out)
        return out
# %%
env.reset()

action_n = env.action_space.n

BATCH_SIZE = 20
GAMMA = 0.999
EPS_START = 0.9
EPS_END = 0.05
EPS_DECAY = 200

model = DQN(action_n)
list(model.parameters())
if use_cuda:
    model.cuda()

optimizer = optim.RMSprop(model.parameters())
memory = ReplayMemory(200)


steps_done = 0
model_actions = []

def select_action(state):
    global steps_done
    sample = random.random()
    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-1. * steps_done / EPS_DECAY)
    steps_done += 1
    if sample > eps_threshold:
        # print(Variable(FloatTensor(state), volatile=True).type(FloatTensor).data.max(0)[1])
        act = model(Variable(FloatTensor(state), volatile=True).type(FloatTensor)).data.max(0)[1].view(1, 1)
        return act
    else:
        return LongTensor([[random.randrange(2)]])

episode_durations = []
last_sync = 0
loss_l = torch.nn.MSELoss()
all_loss = []
tmp = None

def optimize_model():
    global last_sync
    global tmp
    if len(memory) < BATCH_SIZE:
        return
    transitions = memory.sample(BATCH_SIZE)
    batch = Transition(*zip(*transitions))
    non_final_mask = ByteTensor(tuple(map(lambda s: s is not None,
                                          batch.next_state)))
    non_final_next_states = Variable(torch.stack([s for s in batch.next_state
                                                if s is not None]),
                                     volatile=True)
    state_batch = Variable(torch.stack(batch.state))
    action_batch = Variable(torch.cat(batch.action))
    reward_batch = Variable(torch.cat(batch.reward))
    state_action_values = model(state_batch).gather(1, action_batch)
    next_state_values = Variable(torch.zeros(BATCH_SIZE).type(Tensor))
    next_state_values[non_final_mask] = model(non_final_next_states).max(1)[0]
    next_state_values.volatile = False
    # Compute the expected Q values
    expected_state_action_values = (next_state_values * GAMMA) + reward_batch
    tmp = (state_action_values, expected_state_action_values)
    loss = loss_l(state_action_values, expected_state_action_values)
    # print(loss)
    # Optimize the model
    optimizer.zero_grad()
    all_loss.append(loss.data[0])
    loss.backward()
    # for param in model.parameters():
    #     # param.grad.data.clamp_(-1, 1)
    optimizer.step()
# %%
num_episodes = 50
rwrds = []
for i_episode in range(num_episodes):
    state = FloatTensor(env.reset())
    for t in count():
        action = select_action(state)
        st, reward, done, _ = env.step(action[0, 0])
        rwrds.append(reward)
        reward = Tensor([reward])
        if not done:
            next_state = FloatTensor(st)
        else:
            next_state = None

        memory.push(state, action, next_state, reward)
        state = next_state
        optimize_model()
        if done:
            episode_durations.append(t + 1)
            # plot_durations()
            break

print('Complete')
env.render(close=True)
env.close()
plt.ioff()
plt.show()
# %%
plt.plot(episode_durations)
plt.show()
# plt.plot(all_loss)
# plt.show()
# print(tmp)
