# %%
import sys
sys.path.append('C:\Codes\QIQSS-CODE\experiments')
from Pulses.Builder import *
from MyUtils import *

from pyHegel.commands import *

# VARIABLES
path = "C:\\Codes\\QIQSS-CODE\\experiments\\logs\\" # path where to save the data
AWG_SR = 32e4
gain = 1/(0.02512)*0.4

# %% INSTRUMENTS
awg = instruments.tektronix.tektronix_AWG('USB0::0x0699::0x0503::B030793::0')
ats = instruments.ATSBoard(systemId=1, cardId=1)
bilt_9 = instruments.iTest_be214x("TCPIP::192.168.150.112::5025::SOCKET", slot=9)
P1 = instruments.LimitDevice((bilt_9.ramp, {'ch': 1}), min=-3.0, max=3.0)
B1 = instruments.LimitDevice((bilt_9.ramp, {'ch': 2}), min=-3.0, max=3.0)
P2 = instruments.LimitDevice((bilt_9.ramp, {'ch': 3}), min=-3.0, max=3.0)
B2 = instruments.LimitDevice((bilt_9.ramp, {'ch': 4}), min=-3.0, max=3.0)



# %% 1) SPIN-TAIL MAPS

read_list = np.linspace(0.7670, 0.7690, 51)

# pulse shaping
# load center
load = Segment(duration=0.0001, waveform=Ramp(val_start=0.00, val_end=0.00), offset=0.000, mark=(0.0, 1.0))
read = Segment(duration=0.00025, waveform=Ramp(val_start=0.00, val_end=-0.0006), offset=-0.004)
empty = Segment(duration=0.0002, waveform=Ramp(val_start=0.000, val_end=-0.0008), offset=-0.008)

# read center
#load = Segment(duration=0.0002, waveform=Ramp(val_start=0.00, val_end=0.00015), offset=0.002, mark=(0.0, 1.0))
#read = Segment(duration=0.0003, waveform=Ramp(val_start=0.00001, val_end=0.000), offset=0.000)
#empty = Segment(duration=0.0002, waveform=Ramp(val_start=0.000, val_end=-0.00015), offset=-0.002)

pulse = Pulse(load, read, empty)
pulse.addCompensationZeroMean(0.04709)
sendSeqToAWG(awg, pulse, gain, channel=1, run_after=True)
#plotPulse(pulse, AWG_SR)

# ats
configureATS(ats)
ats.acquisition_length_sec.set(0.00055)
ats.nbwindows.set(100)

final_map = []

for i, read_lvl in enumerate(read_list):
    P1.set(read_lvl)
    print('i:{}, P1={}'.format(i, read_lvl))
    
    avg_trace, timelist = acquire(ats, digitize=True, threshold=3.10, sigma=1, return_average_trace=True)
    final_map.append(avg_trace)
awg.run(False)

final_map = np.array(final_map)
#threshold = estimateDigitThreshold(final_map, show_plot=True)

filename = saveNpz(path, "pulse_P1_sweep", final_map, x_axis=timelist, y_axis=read_list, metadata={'pulse':str(pulse), 'ats':ats})

result_dict = loadNpz(filename)
imshowNpz(result_dict, cmap="RdBu_r")


# %% 2) SPIN READOUT

P1.set(0.76825)

# pulse shaping
load = Segment(duration=0.0001, waveform=Ramp(val_start=0.00, val_end=0.00), offset=0.000)
read = Segment(duration=0.00025, waveform=Ramp(val_start=0.00, val_end=-0.0006), offset=-0.004, mark=(0.0, 1.0))
empty = Segment(duration=0.0002, waveform=Ramp(val_start=0.000, val_end=-0.0008), offset=-0.008)
pulse = Pulse(load, read, empty)
pulse.addCompensationZeroMean(0.04709)
sendSeqToAWG(awg, pulse, gain, channel=1)

# ats
configureATS(ats)
ats.acquisition_length_sec.set(read.duration)
ats.nbwindows.set(500)

threshold=3.10
# measure
awg.run(True)
data_all, time = getATSImage(ats, with_time=True) # [[trace0], [trace1], ..., [traceNWindow]], [t0, t1, ..., t_SR*AcquisitionLength]
awg.run(False)

# post-process
filt_map = gaussianLineByLine(data_all, sigma=1)
digit_map = digitize(filt_map, threshold)

#imshow(data_all, x_axis=time)
#imshow(digit_map, x_axis=time)

data_avg = averageLines(data_all)
digit_avg = averageLines(digit_map)
qplot(time, data_avg, title=f"P1:{P1.get()}, no digit")
qplot(time, digit_avg, title=f"P1:{P1.get()}, digit")


filename = saveNpz(path, "readout_digit", digit_map, x_axis=time, metadata={'pulse':str(pulse), 'ats':ats, 'P1':str(P1.get())})

events_spins = countEvents(digit_map, time, one_out_only=True)
print(events_spins)

spin_stat = classifyTraces(digit_map, time)
print(spin_stat)

# %% 3) T1

len_list = np.linspace(0.00001, 0.010, 150)


# ats
configureATS(ats)
ats.acquisition_length_sec.set(0.00025)
ats.nbwindows.set(1000)

threshold = 3.10
maps = []
events = []
spin_stats = []

for i, load_time in enumerate(len_list):
    print('i:{}, load_time={}'.format(i, load_time))
    
    load = Segment(duration=load_time, waveform=Ramp(val_start=0.00, val_end=0.00), offset=0.000)
    read = Segment(duration=0.00025, waveform=Ramp(val_start=0.00, val_end=-0.0006), offset=-0.004, mark=(0.0, 1.0))
    empty = Segment(duration=0.0002, waveform=Ramp(val_start=0.000, val_end=-0.0008), offset=-0.008)
    pulse = Pulse(load, read, empty)
    pulse.addCompensationZeroMean(0.04709)
    sendSeqToAWG(awg, pulse, gain, run_after=True)
    
    data_digit, time = acquire(ats, digitize=True, threshold=threshold, sigma=1)
    awg.run(False)
        
    maps.append(data_digit)


    events.append(countEvents(data_digit, time, one_out_only=True))
    spin_stats.append(classifyTraces(data_digit, time)['avg_spin_up'])

twait_list = len_list + pulse.segments[-1].duration

maps = np.array(maps)
events = np.array(events)
spin_stats = np.array(spin_stats)

#filename = saveNpz(path, "t1_data", maps, metadata={'pulse':str(pulse), 'ats':ats})
filename = saveNpz(path, "spin", spin_stats, metadata={'pulse':str(pulse), 'ats':ats, 'twait_list':twait_list})

qplot(twait_list, events[:,0], 'twait', 'P spin up')
qplot(twait_list, spin_stats, 'twait', 'P spin up', same_fig=True)

fit.fitplot(_exp, twait_list, events[:,0], p0=[0.0005, 0.3, 0, 0.1])
fit.fitplot(_exp, twait_list, spin_stats, p0=[0.0005, 0.3, 0, 0.1])




