'''
custom metrics for the neuron project 
This module is currently very experimental...
'''

import numpy as np
import keras.backend as K

# medipy package 
import sys
sys.path.append("C:\\Users\\adalca\\Dropbox (Personal)\\code\\python\\medipy-lib")
import medipy.metrics

class Dice(object):
    ''' UNTESTED
    Dice-based metric(s)

    Variables:
        labels: optional numpy array of shape (L,) where L is the number of labels to be evaluated.
            if not provided, all non-background (0) labels are computed and averaged
        weights: optional numpy array of shape (L,) giving relative weights of each label
        prior: filename of spatial priors to be added to y_pred before Dice
            TODO: maybe move this to a 'Prior' layer with a set weight in architecture ?


    Usage
        diceloss = metrics.dice([1, 2, 3])
        model.compile(diceloss, ...)
    '''

    def __init__(self, labels=None, weights=None, prior=None):
        self.labels = labels
        self.weights = weights

        # process prior
        if prior is not None:
            data = np.load(prior)
            loc_vol = data['prior']
            loc_vol = np.expand_dims(loc_vol, axis=0) # reshape for model
            loc_vol /= np.sum(loc_vol, axis=-1, keepdims=True)
            self.log_prior = np.log(loc_vol)
        else:
            self.log_prior = None

    def loss(self, y_true, y_pred):
        ''' the loss. Assumes y_pred is prob (in [0,1] and sum_row = 1) '''

        y_pred_np = np.log(y_pred.eval())
        if self.log_prior is not None:
            y_pred_np = y_pred_np + self.log_prior
        lab_pred = np.argmax(y_pred_np)
        lab_true = np.argmax(y_true.eval())

        # compute dice measure
        dicem = medipy.metrics.dice(lab_true, lab_pred, self.labels)

        # weight the labels
        if self.weights is not None:
            dicem *= self.weights

        # return negative mean dice as loss
        return K.variable(-np.mean(dicem))



class CategoricalCrossentropy(object):
    ''' UNTESTED
    Categorical crossentropy with optional weights and spatial prior

    Adapted from weighted categorical crossentropy via wassname:
    https://gist.github.com/wassname/ce364fddfc8a025bfab4348cf5de852d

    Variables:
        weights: numpy array of shape (C,) where C is the number of classes
        prior:

    Usage:
        loss = CategoricalCrossentropy().loss # or
        loss = CategoricalCrossentropy(weights=weights).loss # or
        loss = CategoricalCrossentropy(..., prior=prior).loss
        model.compile(loss=loss,optimizer='adam')
    '''

    def __init__(self, weights=None, prior=None):
        self.weights = weights if (weights is not None) else K.variable(weights)

        # process prior
        if prior is not None:
            data = np.load(prior)
            loc_vol = data['prior']
            loc_vol = np.expand_dims(loc_vol, axis=0) # reshape for model
            self.log_prior = K.log(K.clip(K.variable(loc_vol), K.epsilon(), 1))
        else:
            self.log_prior = None

    def loss(self, y_true, y_pred):
        ''' categorical crossentropy loss '''
        # scale preds so that the class probas of each sample sum to 1
        y_pred /= K.sum(y_pred, axis=-1, keepdims=True)
        # clip
        y_pred = K.clip(y_pred, K.epsilon(), 1)

        # combine
        log_post = K.log(y_pred)
        if self.log_prior is not None:
            log_post += self.log_prior

        # calc
        p = y_true * log_post
        loss = p
        if self.weights is not None:
            loss *= self.weights

        loss = -K.sum(loss, -1)
        return K.mean(loss)



class Nonbg(object):
    ''' UNTESTED
    class to modify output on operating only on the non-bg class

    All data is aggregated and the (passed) metric is called on flattened true and
    predicted outputs in all (true) non-bg regions

    Usage:
        loss = metrics.dice
        nonbgloss = nonbg(loss).loss
    '''

    def __init__(self, metric):
        self.metric = metric

    def loss(self, y_true, y_pred):
        ''' prepare a loss of the given metric/loss operating on non-bg data '''
        yt = y_true.eval()
        ytbg = np.where(yt == 0)
        y_true_fix = K.variable(yt.flat(ytbg))
        y_pred_fix = K.variable(y_pred.eval().flat(ytbg))
        return self.metric(y_true_fix, y_pred_fix)
