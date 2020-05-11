#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 16:40:31 2020

@author: jeremyjohnston
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf
import numpy as np

tf.keras.backend.clear_session()  # For easy reset of notebook state.

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import losses
from tensorflow.python.framework import ops
from tensorflow.python.keras import backend as K
from tensorflow.python.ops import math_ops
import tensorflow_probability as tfp

class MeanPercentageSquaredError(tf.keras.losses.Loss):
    def call(self, y_true, y_pred):
      y_pred = ops.convert_to_tensor(y_pred)
      y_true = math_ops.cast(y_true, y_pred.dtype)
      err_norm = tf.math.reduce_sum(math_ops.square(y_pred - y_true),axis=-1)
      y_true_norm = tf.math.reduce_sum(math_ops.square(y_true),axis=-1)
      return K.mean(tf.math.divide(err_norm,y_true_norm))

class ISTANet(tf.keras.Model):
  
  def __init__(self, p, num_stages = 20, *args, **kwargs):
    super().__init__()
    self.params_init = {'lambda':0.1}
    self.n1 = p.size(1)

    if 'params_init' in kwargs.keys():
      for k,v in kwargs['params_init'].items():
        self.params_init[k] = v

    if 'tied' in args:
      self.tied = 'tied'
    elif 'untied' in args:
      self.tied = 'untied'

    self.Layers=[]
    for i in range(num_stages):
      self.Layers.append(x_update(self.params_init,p,*args))
    
    print('LISTA-Net with {0} stages and initial parameters:'.format(len(self.Layers)))
    print('Scenario:','{0}x{1}'.format(p.size(0),p.size(1)),p.scen)
    for k,v in self.params_init.items():
      print(k,'=',v)

  def call(self, inputs):
    x_0 = np.zeros((self.n1,1),dtype=np.float32)
    x = self.Layers[0](inputs, x_0)
    for l in self.Layers[1:]:
      x = l(inputs,x)
    return tf.transpose(x)
    
    
class x_update(layers.Layer):

  def __init__(self, params_init, p, *args, **kwargs):
    super().__init__()
    # p = kwargs['problem']
    m = p.size(0);
    n = p.size(1);
    # beta = 1/np.sum(p.A**2)
    beta = 1/np.max(np.linalg.eigvals(np.matmul(p.A.T.conj(),p.A)))
    if 'blank' in args:
      B_init = np.zeros((n,m))  
      S_init = np.zeros((n,n))
    else:
      B_init = beta*p.A.T.conj()
      S_init = np.eye(n) - np.matmul(B_init,p.A)
      
    # lambda_init = p.lambda_init_lista*np.ones((n,1),dtype=np.float32)  

    if 'tied' in args:
      tied = True
    else:
      tied = False

    self.S = tf.Variable(initial_value=S_init.astype(np.float32),
                         trainable=not tied, name='S')
    self.B = tf.Variable(initial_value=B_init.astype(np.float32),
                         trainable=not tied, name='B')

    self.lamb = tf.Variable(initial_value=params_init['lambda'],
                            trainable=True, name='lambda')
                          

  def call(self, y, x):
    return tfp.math.soft_threshold(tf.matmul(self.S,x) + tf.matmul(self.B,tf.transpose(y)), self.lamb)

