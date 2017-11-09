import numpy as np
import matplotlib.pyplot as plt


fs = 125       # sampling rate, Hz, must be integer
duration = 2   # in seconds, may be float
f = 4.0        # sine frequency, Hz, may be float

# generate samples, note conversion to float32 array
samples = np.random.rand(125) - 0.5
it = np.nditer(samples, flags=['f_index'], op_flags=['readwrite'])
while not it.finished:
    it[0] = it[0] + (np.sin(2 * np.pi * 10 * (it.index / 125.0)) + np.sin(2 * np.pi * 2 * (it.index / 125.0)) * .25)
    it.iternext()

print(samples)
# samples = (np.sin(2*np.pi*np.arange(fs*duration)*f/fs)).astype(np.float32)


# alpha = np.sin(2 * np.pi * 7.5 * (i / 125))
# beta = np.sin(2 * np.pi * 2 * (i / 125)) * .25

plt.plot(range(len(samples)), samples)
plt.show()


ps = np.abs(np.fft.fft(samples))**2 #power spectrum

time_step = 1.0 / 125
freqs = np.fft.fftfreq(len(samples), time_step)
idx = np.argsort(freqs)

#find the peak alpha frequency



axes = plt.gca()
axes.set_xlim([min(freqs),max(freqs)])
# axes.set_ylim([min(ps[0]),max(ps[0])])

plt.plot(freqs[idx], ps[idx])
plt.show()

