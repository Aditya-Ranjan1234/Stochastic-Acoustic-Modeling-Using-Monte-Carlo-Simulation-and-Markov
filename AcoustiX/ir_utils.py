import numpy as np
from scipy import stats

def compute_metric(ir, fs):
    """Compute the relevant impulse response parameters

    Parameters
    ----------
    ir : np.array 
        ir data
    fs : float 
        sampling rate

    Returns
    -------
    energy: energy curve
    t60: RT60 parameter
    C50: C50 dB
    """
    energy = 10 * np.log10(np.cumsum(ir[::-1]**2)[::-1] / sum(ir**2))
    samples_50ms = int(0.05 * fs)  # Number of samples in 50 ms
    energy_ori_early = np.sum(ir[0:samples_50ms]**2)
    energy_ori_late = np.sum(ir[samples_50ms:]**2)

    C50 = 10.0 * np.log10(energy_ori_early / energy_ori_late)
    init_db = -5
    end_db = -25
    factor = 3
    
    # find the intersection of -5db and -25db position
    energy_init = energy[np.abs(energy - init_db).argmin()]
    energy_end = energy[np.abs(energy - end_db).argmin()]
    init_sample = np.where(energy == energy_init)[0][0]
    end_sample = np.where(energy == energy_end)[0][0]
    x = np.arange(init_sample, end_sample + 1) / fs
    y = energy[init_sample:end_sample + 1]
    
    # regress to find the db decay trend
    slope, intercept = stats.linregress(x, y)[0:2]
    db_regress_init = (init_db - intercept) / slope
    db_regress_end = (end_db - intercept) / slope

    t60_linear = factor * (db_regress_end - db_regress_init)

    return energy, t60_linear, C50


