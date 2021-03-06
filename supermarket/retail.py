from time import sleep
from datetime import datetime, timedelta
import random
from dispatcher import Dispatch
import os
import uuid

class SuperMarket():
  def __init__(self):
    self.drone_params = {}
    self.param_names = ['order_id', 'order_placed_at', 'weight', 'distance', 'packaging_duration', 'price', 'order_sent_at', 'order_completed_at']
    [self.init_drone_params(idx) for idx in range(self.drone_n)]

  def get_current_time(self):
    with open(self.data_path, 'r') as f:
      last_order_completed_at = f.readlines()[-1].split(',')[-1]

    if 'order_completed_at' not in last_order_completed_at:
      return datetime.strptime(last_order_completed_at, "%Y-%m-%d %H:%M:%S.%f")
    else:
      return datetime.now()

  def init_drone_params(self, drone_idx):
    self.drone_params[drone_idx] = {'is_dispatched': False}
    for name in self.param_names:
      self.drone_params[drone_idx][name] = None

  @staticmethod
  def get_rand_value(ranges_start, ranges_probs):
    start = random.choices(ranges_start, ranges_probs)[0]
    end_idx = ranges_start.index(start) + 1
    range_end = ranges_start[end_idx]
    return random.randint(start, range_end)

  def place_order(self):
    return self.time_now, \
      self.get_rand_value(self.weight_ranges_start, self.weight_ranges_probs), \
      self.get_rand_value(self.distance_ranges_start, self.distance_ranges_probs)
      
  def pack_order(self, weight):
    packages = [self.get_package_weight(weight)]
    weight -= self.max_drone_load
    while weight > 0:
      packages.append(self.get_package_weight(weight))
      weight -= self.max_drone_load
    return packages, max([2, weight / 7.5])

  def get_package_weight(self, weight):
    return min([self.max_drone_load, weight])

  def get_free_drone_idx(self):
    return [drone_idx for drone_idx, params in self.drone_params.items() if params['is_dispatched'] is False]

  def get_returned_drone_idx(self):
    return [drone_idx for drone_idx, params in self.drone_params.items() if params['is_dispatched'] is None]

  def command_dispatch(self, drone_idx, order_placed_at, weight, distance, packaging_duration):
    self.drone_params[drone_idx]['order_id'] = uuid.uuid4()
    self.drone_params[drone_idx]['order_placed_at'] = order_placed_at
    self.drone_params[drone_idx]['weight'] = weight
    self.drone_params[drone_idx]['distance'] = distance
    self.drone_params[drone_idx]['packaging_duration'] = packaging_duration
    self.drone_params[drone_idx]['price'] = self.price_per_kg * weight + self.price_per_km * distance
    self.drone_params[drone_idx]['is_dispatched'] = True
    return Dispatch(self.drone_params, drone_idx, self.max_drone_speed, self.time_factor)

  def write_data(self, drone_idxs):
    log_data = '\n'
    for drone_idx in drone_idxs:
      params = ','.join([str(self.drone_params[drone_idx][param]) for param in self.param_names])
      log_data += f'{drone_idx},{params}\n'

    if len(log_data) > 1:
      with open(self.data_path, 'a') as f:
        f.write(log_data[:-1])

  def handle_orders(self):
    order_placed_at, weight, distance = self.place_order()
    packages, packaging_duration = self.pack_order(weight)
    
    while len(self.get_free_drone_idx()) < len(packages):
      drone_idxs = self.get_returned_drone_idx()
      self.write_data(drone_idxs)
      [self.init_drone_params(drone_idx) for drone_idx in drone_idxs]
      if len(drone_idxs) == 0:
        sleep(0.1)

    dispatches = [
      self.command_dispatch(drone_idx, order_placed_at, weight, distance, packaging_duration)
      for drone_idx, weight in zip(self.get_free_drone_idx(), packages)
    ]
    [d.start() for d in dispatches]

    self.time_now += timedelta(minutes=packaging_duration)
    sleep(0.1)