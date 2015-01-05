# -*- coding: utf-8 -*-
"""
Design equiripple-Filters (LP, HP, BP, BS) with fixed or minimum order, return
the filter design in zeros, poles, gain (zpk) format
Created on Tue Nov 26 12:13:41 2013

@author: Christian Muenker

Zu erwartende Änderungen in scipy 0.15:
https://github.com/scipy/scipy/pull/3717
https://github.com/scipy/scipy/issues/2444
"""
from __future__ import print_function, division
import scipy.signal as sig
import numpy as np
from numpy import log10, pi, arctan

# TODO: BS does not work correctly (-> odd order!)
# TODO: Try HP with even order & type = Hilbert

zpkba = 'ba' # set output format of filter design routines to 'zpk' or 'ba'
             # currently, only 'ba' is supported for equiripple routines

class equiripple(object):
    
    def __init__(self):
        self.name = {'equiripple':'Equiripple'}
        self.msg_man = "Enter a weight value for each band below"
        self.msg_min = ""
        
        self.ft = 'FIR'
        self.rt = {
            "LP": {"man":{"par":['N', 'W_pb', 'W_sb', 'F_pb', 'F_sb'],
                          "vis":['fo','fs', 'Ws']},
                   "min":{"par":['A_pb','A_sb','F_pb','F_sb']}},
            "HP": {"man":{"par":['N', 'W_sb', 'W_pb', 'F_sb','F_pb']},
                   "min":{"par":['A_pb','A_sb','F_sb','F_pb']}},
            "BP": {"man":{"par":['N', 'F_sb', 'F_pb', 'F_pb2', 'F_sb2',
                        'W_sb', 'W_pb', 'W_sb2']}},
            "BS": {"man":{"par":['N', 'F_pb', 'F_sb', 'F_sb2', 'F_pb2',
                        'W_pb', 'W_sb', 'W_pb2']}}
          #"HIL":
          #"DIFF":
                   }
        self.info = "Equiripple-Filter haben im Passband und im Stopband \
        jeweils konstanten Ripple, sie nutzen das vorgegebene Toleranzband \
        jeweils voll aus."

    def zpk2ba(self, arg):
        """ 
        Convert poles / zeros / gain to filter coefficients (polynomes) and the
        other way round
        """
        if zpkba == 'zpk': # arg = [z,p,k]
            self.coeffs = sig.zpk2tf(arg[0], arg[1], arg[2])        
            self.zpk = arg
        else: # arg = [b,a]
            self.zpk = sig.tf2zpk(arg[0], arg[1])#[np.roots(arg), [1, np.zeros(len(arg)-1)],1]
            self.coeffs = arg   

    def LPman(self, specs):
        self.zpk2ba(sig.remez(specs['N'],[0, specs['F_pb'], specs['F_sb'], 
                0.5],[1, 0], weight = [specs['W_pb'],specs['W_sb']], Hz = 1))

    def HPman(self, specs):
        N = self.oddround(specs['N']) # enforce odd order 
        self.zpk2ba(sig.remez(N,[0, specs['F_sb'], specs['F_pb'], 
                0.5],[0, 1], weight = [specs['W_sb'],specs['W_pb']], Hz = 1))
        
    # For BP and BS, F_pb and F_sb have two elements each
    def BPman(self, specs):
        self.zpk2ba(sig.remez(specs['N'],[0, specs['F_sb'], specs['F_pb'], 
                specs['F_pb2'], specs['F_sb2'], 0.5],[0, 1, 0], 
                weight = [specs['W_sb'],specs['W_pb'], specs['W_sb2']], Hz = 1))

    def BSman(self, specs):
        self.zpk2ba(sig.remez(specs['N'],[0, specs['F_pb'], specs['F_sb'], 
                specs['F_sb2'], specs['F_pb2'], 0.5],[1, 0, 1], 
                weight = [specs['W_pb'],specs['W_sb'], specs['W_pb2']], Hz = 1))
                
    def LPmin(self, specs):
        A_PB_lin = (10**(specs['A_pb']/20.0)-1) / (10**(specs['A_pb']/20.0)+1)*2
        print(A_PB_lin)
        (L, F, A, W) = self.remezord([specs['F_pb'], specs['F_sb']], [1, 0], 
            [A_PB_lin, 10.**(-specs['A_sb']/20)], Hz = 1, alg = 'ichige')
        self.zpk2ba(sig.remez(L, [0, specs['F_pb'], specs['F_sb'], 
                0.5],[1, 0], weight = W, Hz = 1))
                
    def HPmin(self, specs):
        A_PB_lin = (10**(specs['A_pb']/20.0)-1) / (10**(specs['A_pb']/20.0)+1)*2
        print(A_PB_lin)
        (L, F, A, W) = self.remezord([specs['F_sb'], specs['F_pb']], [0, 1], 
            [np.sqrt(2)*10.**(-specs['A_sb']/20), A_PB_lin], Hz = 1, alg = 'ichige')
        N = self.oddround(L)  # enforce odd order 

        self.zpk2ba(sig.remez(N, [0, specs['F_sb'], specs['F_pb'], 
                0.5],[0, 1], weight = W, Hz = 1, type = 'bandpass'))
        
                
                
    #========================================================
    """Supplies remezord method according to Scipy Ticket #475
    http://projects.scipy.org/scipy/ticket/475
    https://github.com/thorstenkranz/eegpy/blob/master/eegpy/filter/remezord.py
    """
    
    #from numpy import mintypecode
    
     
    abs = np.absolute
     
    def oddround(self, x):
        """Return the nearest odd integer from x."""
    
        return x-np.mod(x,2)+1
    
    def oddceil(self, x):
        """Return the smallest odd integer not less than x."""
    
        return self.oddround(x+1)
        
    def remlplen_herrmann(self, fp,fs,dp,ds):
        """
    Determine the length of the low pass filter with passband frequency
    fp, stopband frequency fs, passband ripple dp, and stopband ripple ds.
    fp and fs must be normalized with respect to the sampling frequency.
    Note that the filter order is one less than the filter length.
    
    Uses approximation algorithm described by Herrmann et al.:
    
    O. Herrmann, L.R. Raviner, and D.S.K. Chan, Practical Design Rules for
    Optimum Finite Impulse Response Low-Pass Digital Filters, Bell Syst. Tech.
    Jour., 52(6):769-799, Jul./Aug. 1973.
    """
    
        dF = fs-fp
        a = [5.309e-3,7.114e-2,-4.761e-1,-2.66e-3,-5.941e-1,-4.278e-1]
        b = [11.01217, 0.51244]
        Dinf = log10(ds)*(a[0]*log10(dp)**2+a[1]*log10(dp)+a[2])+ \
               a[3]*log10(dp)**2+a[4]*log10(dp)+a[5]
        f = b[0]+b[1]*(log10(dp)-log10(ds))
        N1 = Dinf/dF-f*dF+1
    
        return int(self.oddround(N1))
    
    def remlplen_kaiser(self, fp,fs,dp,ds):
        """
    Determine the length of the low pass filter with passband frequency
    fp, stopband frequency fs, passband ripple dp, and stopband ripple ds.
    fp and fs must be normalized with respect to the sampling frequency.
    Note that the filter order is one less than the filter length.
    
    Uses approximation algorithm described by Kaiser:
    
    J.F. Kaiser, Nonrecursive Digital Filter Design Using I_0-sinh Window
    function, Proc. IEEE Int. Symp. Circuits and Systems, 20-23, April 1974.
    """
    
        dF = fs-fp
        N2 = (-20*log10(np.sqrt(dp*ds))-13.0)/(14.6*dF)+1.0
    
        return int(self.oddceil(N2))
    
    def remlplen_ichige(self, fp,fs,dp,ds):
        """
    Determine the length of the low pass filter with passband frequency
    fp, stopband frequency fs, passband ripple dp, and stopband ripple ds.
    fp and fs must be normalized with respect to the sampling frequency.
    Note that the filter order is one less than the filter length.
    Uses approximation algorithm described by Ichige et al.:
    K. Ichige, M. Iwaki, and R. Ishii, Accurate Estimation of Minimum
    Filter Length for Optimum FIR Digital Filters, IEEE Transactions on
    Circuits and Systems, 47(10):1008-1017, October 2000.
    """
        dp_lin = (10**(dp/20.0)-1) / (10**(dp/20.0)+1)*2
        dF = fs-fp
        v = lambda dF,dp:2.325*((-log10(dp))**-0.445)*dF**(-1.39)
        g = lambda fp,dF,d:(2.0/pi)*arctan(v(dF,dp)*(1.0/fp-1.0/(0.5-dF)))
        h = lambda fp,dF,c:(2.0/pi)*arctan((c/dF)*(1.0/fp-1.0/(0.5-dF)))
        Nc = np.ceil(1.0+(1.101/dF)*(-log10(2.0*dp))**1.1)
        Nm = (0.52/dF)*log10(dp/ds)*(-log10(dp))**0.17
        N3 = np.ceil(Nc*(g(fp,dF,dp)+g(0.5-dF-fp,dF,dp)+1.0)/3.0)
        DN = np.ceil(Nm*(h(fp,dF,1.1)-(h(0.5-dF-fp,dF,0.29)-1.0)/2.0))
        N4 = N3+DN
        
        return int(N4)
    
    def remezord(self, freqs,amps,rips,Hz=1,alg='ichige'):
        """
        Filter parameter selection for the Remez exchange algorithm.
    
    Calculate the parameters required by the Remez exchange algorithm to
    construct a finite impulse response (FIR) filter that approximately
    meets the specified design.
    
    Parameters
    ----------
    
        freqs : list
            A monotonic sequence of band edges specified in Hertz. All elements 
            must be non-negative and less than 1/2 the sampling frequency as 
            given by the Hz parameter. The band edges "0" and "f_S / 2" do not 
            have to be specified, hence  2 * number(amps) - 2 freqs are needed.
        
        amps : list
            A sequence containing the amplitudes of the signal to be 
            filtered over the various bands, e.g. 1 for the passband, 0 for the
            stopband and 0.42 for some intermediate band.
        
        rips : list 
            A list with the peak ripples (linear, not in dB!) for each band. For 
            the stop band this is equivalent to the minimum attenuation.
            
        Hz : float
            Sampling frequency
        
        alg : string
            Filter length approximation algorithm. May be either 'herrmann',
            'kaiser' or 'ichige'. Depending on the specifications, some of
            the algorithms may give better results than the others.
    
    Returns
    -------
    
    numtaps,bands,desired,weight -- See help for the remez function.
    
    Examples
    --------
            We want to design a lowpass with the band edges of 40 resp. 50 Hz and a 
            sampling frequency of 200 Hz, a passband peak ripple of 10% 
            and a stop band ripple of 0.01 or 40 dB.
        >>> (L, F, A, W) = remezord([40, 50], [1, 0], [0.1, 0.01], Hz = 200)
            
    
    
    """
    
        # Make sure the parameters are floating point numpy arrays:
        freqs = np.asarray(freqs,'d')
        amps = np.asarray(amps,'d')
        rips = np.asarray(rips,'d')
    
        # Scale ripples with respect to band amplitudes:
        rips /= (amps+(amps==0.0))
    
        # Normalize input frequencies with respect to sampling frequency:
        freqs /= Hz
    
        # Select filter length approximation algorithm:
        if alg == 'herrmann':
            remlplen = self.remlplen_herrmann
        elif alg == 'kaiser':
            remlplen = self.remlplen_kaiser
        elif alg == 'ichige':
            remlplen = self.remlplen_ichige
        else:
            raise ValueError('Unknown filter length approximation algorithm.')
        
        # Validate inputs:
        if any(freqs > 0.5):
            raise ValueError('Frequency band edges must not exceed the Nyquist frequency.')
        if any(freqs < 0.0):
            raise ValueError('Frequency band edges must be nonnegative.')
        if any(rips <= 0.0):
            raise ValueError('Ripples must be nonnegative and non-zero.')
        if len(amps) != len(rips):
            raise ValueError('Number of amplitudes must equal number of ripples.')
        if len(freqs) != 2*(len(amps)-1):
            raise ValueError('Number of band edges must equal 2*(number of amplitudes-1)')
    
    
        # Find the longest filter length needed to implement any of the
        # low-pass or high-pass filters with the specified edges:
        f1 = freqs[0:-1:2]
        f2 = freqs[1::2]
        L = 0
        for i in range(len(amps)-1):
            L = max((L,
                     remlplen(f1[i],f2[i],rips[i],rips[i+1]),
                     remlplen(0.5-f2[i],0.5-f1[i],rips[i+1],rips[i])))
    
        # Cap the sequence of band edges with the limits of the digital frequency
        # range:
        bands = np.hstack((0.0,freqs,0.5))
    
        # The filter design weights correspond to the ratios between the maximum
        # ripple and all of the other ripples:
        weight = max(rips)/rips
        
        return [L,bands,amps,weight]
    
    
            