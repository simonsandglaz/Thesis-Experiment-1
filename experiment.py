from __future__ import print_function

from psychopy import visual
from psychopy import core, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import time, numpy as np, random
import scipy.signal
import pyedflib
import os
import errno
import scipy.ndimage.filters as filters

from pylsl import StreamInlet, resolve_stream
from pylsl import StreamInfo, StreamOutlet

import matplotlib.pyplot as plt
import matlab.engine

eng = matlab.engine.start_matlab()

sample_rate = 125 # 125Hz in 16 channel mode for openBCI
# window_x = 3840
# window_y = 2160

window_x = 1920
window_y = 1080

text_height = 28

channels = {'Fpz': 0,
            'Fp1': 1,
            'AF3': 2,
            'FC1': 3,
            'Fz': 4,
            'FC2': 5,
            'AF4': 6,
            'Fp2': 7,
            'Oz': 8,
            'PO4': 9,
            'P4': 10,
            'CP2': 11,
            'Pz': 12,
            'CP1': 13,
            'P3': 14,
            'PO3': 15}

index2channel = {}
for channel, channel_number in channels.items():
    index2channel[channel_number] = channel

# Experiment Details
# 1. Meditation without feedback (2 runs, 4 minutes each)
# 2. Meditation with offline feedback (feedback graph shown offline after each run; 4 runs, 1.5 minutes each)
# 3. Meditation with real-time feedback (3 runs, 1.5 minutes each)
# 4. "Free-play" session. Participants are allowed to experiment with the feedback, using strategies of their own choosing. (2 runs, 7 minutes each).
# 5. Participants are asked to control the feedback signal in the direction that corresponds to effortless awareness.
#   Participants are not instructed on a particular strategy for doing this,
#   but reminded to draw on previous experience meditating and experimenting with the feedback earlier in the experiment. (3 runs, 1.5 minutes each)
# 6. Participants are asked to control the feedback signal in the direction that corresponds to the opposite of effortless awareness.
#   Again, participants are not instructed on a particular strategy for doing this, in the same way as 5) (5 runs, 1.5 minutes each)

subject_id = 1

def main():
    try:  # try to get a previous parameters file
        expInfo = fromFile('lastParams.test')
    except:  # if not there then use a default set
        expInfo = {'observer': 'Simon', 'subject_id': 0}
    expInfo['dateStr'] = data.getDateStr()  # add the current time
    expInfo['subject_id'] = expInfo['subject_id'] + 1

    if "group" in expInfo.keys() and expInfo["group"] == "sham":
        expInfo["group"] = "experiment"
    else:
        expInfo["group"] = "sham"

    print(expInfo["group"])
    # present a dialogue to change params
    dlg = gui.DlgFromDict(expInfo, title='Thesis Experiment 1', fixed=['dateStr'])
    if dlg.OK:
        toFile('lastParams.test', expInfo)  # save params to file for next time
    else:
        core.quit()  # the user hit cancel so exit
        
    inlet, outlet = connect_to_EEG()

    #read stimuli adjectives for baseline task
    priming_stimuli = read_priming_stimuli()

    #set up experiment window
    win = visual.Window([window_x,window_y], allowGUI=True, monitor='testMonitor', units='pix', fullscr=False)

    subject_id = expInfo["subject_id"]
    stimuli_index = 0


    # 1. Meditation without feedback (2 runs, 4 minutes each)
    # for i in range(2):
    #     baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
    #     save_edf(eeg, events, subject_id, 0, i, 'baseline')
    #     eeg, events = show_no_feedback(win, inlet, outlet, baseline, ipaf)
    #     save_edf(eeg, events, subject_id, 0, i, 'trial')
    #
    #     show_meditation_only_questions(win, subject_id, 0, i)
    #     stimuli_index += 1

    # 2. Meditation with offline feedback (feedback graph shown offline after each run; 4 runs, 1.5 minutes each)
    # for i in range(3):
    #     baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
    #     save_edf(eeg, events, subject_id, 1, i, 'baseline')
    #
    #     message1 = visual.TextStim(win, pos=[0, +20], text='Please perform the instructed meditation practice', height=text_height)
    #     message2 = visual.TextStim(win, pos=[0, -20], text="Press a key when ready.", height=text_height)
    #     message1.draw()
    #     message2.draw()
    #     win.flip()
    #     event.waitKeys()
    #
    #     eeg, events, feedback_stimuli, feedback_values = show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf)
    #     save_edf(eeg, events, subject_id, 1, i, 'trial')
    #     show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 1, i)
    #     if i == 3:
    #         show_final_feedback_questions(win, 1, i)
    #     stimuli_index += 1

    # 3. Meditation with real-time feedback (4 runs, 1.5 minutes each)
    for i in range(3):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 2, i, 'baseline')

        sham_stimuli = []
        if expInfo["group"] == "sham":
            sham_stimuli, feedback_values = stimuli_from_eeg(win, subject_id, 2, i)

        message1 = visual.TextStim(win, pos=[0, +40], text='Please perform the instructed meditation practice', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        if expInfo["group"] == "sham":
            eeg, events, feedback_stimuli = show_sham_feedback(win, inlet, outlet, sham_stimuli, 5400)
        else:
            eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 2, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 3:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    # 4. "Free-play" session. Participants are allowed to experiment with the feedback, using strategies of their own choosing. (2 runs, 7 minutes each).
    for i in range(2):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 3, i, 'baseline')

        message1 = visual.TextStim(win, pos=[0, +40], text='Experiment with methods to manipulate the graph', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        eeg, events = show_neurofeedback_free_play(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 3, i, 'trial')
        stimuli_index += 1

    # 5. Volitional control in direction of effortless awareness
    for i in range(3):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 4, i, 'baseline')

        message1 = visual.TextStim(win, pos=[0, +40], text='Please try to make the graph go in the direction that you think corresponds to increased effortlessness of awareness', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 4, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 3:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    # 6. Volitional control in direction of opposite effortless awareness
    for i in range(3):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 5, i, 'baseline')

        message1 = visual.TextStim(win, pos=[0, +40], text='Please try to make the graph go in the direction that you think corresponds to decreased effortlessness of awareness', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 5, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 3:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    win.close()
    core.quit()

def show_baseline(win, inlet, outlet, priming_stimulus):

    # show some priming stimuli while recording baseline data
    priming_length = 1800 # 30 seconds
    # priming_length = 900
    fixation_length = 60 # 1 second
    stimulus_length = 180 # 3 seconds
    artifact_length_remaining = 0
    frames_per_bar = 60
    bars = 0

    message1 = visual.TextStim(win, pos=[0,+40],text='Consider how the following word describes you', height=text_height)
    message2 = visual.TextStim(win, pos=[0,-40],text="Press a key when ready.", height=text_height)
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    outlet.push_sample(['baseline_start'])

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=0.2)
    peak_alpha_channels = [channels["Oz"],
                              channels["PO3"],
                              channels["PO4"]]

    baseline_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]

    full_eeg = [[] for i in range(len(channels))]
    full_eeg_no_artifacts = [[] for i in range(len(channels))]

    events = []


    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length/60))
    for frameN in range(priming_length):
        chunk, timestamps = inlet.pull_chunk()

        if 0 <= frameN < fixation_length:  # present fixation for a subset of frames
            fixation.draw()
        if fixation_length <= frameN < stimulus_length + fixation_length:
            if frameN == fixation_length + 1:
                events.append(EEGEvent("priming_stimulus", trialClock.getTime(), priming_stimulus))
            visual.TextStim(win, pos=[0, 0], text=priming_stimulus).draw()  # trait-adjective

        if fixation_length + stimulus_length <= frameN < priming_length + fixation_length:  # present stim for a different subset
            for sample in chunk:  # put new samples in the eeg buffer
                frontal_samples = [sample[i] for i in baseline_channels]
                if max(frontal_samples) > 80:
                    events.append(EEGEvent("eye_blink_artifact", 0, 1))
                    artifact_length_remaining = 25
                    print("eye blink")

                if artifact_length_remaining == 0:
                    for index, channel_data in enumerate(sample):
                        full_eeg_no_artifacts[index].append(channel_data)
                else:
                    artifact_length_remaining -= 1

                for index, channel_data in enumerate(sample):
                    full_eeg[index].append(channel_data)

        win.flip()

    frontal_eeg = [full_eeg[i] for i in baseline_channels]

    peak_alpha = np.mean(map(lambda samples: individual_peak_alpha(samples), [full_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg[i] for i in baseline_channels]))

    return baseline_frontal_alpha_power, peak_alpha, full_eeg, events

def show_baseline_with_graph(win, inlet, outlet, priming_stimulus):

    # show some priming stimuli while recording baseline data
    priming_length = 1800 # 30 seconds
    # priming_length = 900
    fixation_length = 60 # 1 second
    stimulus_length = 180 # 3 seconds
    artifact_length_remaining = 0
    frames_per_bar = 60
    bars = 0

    feedback_stimuli = baseline_feedback(win, priming_length, 190)

    message1 = visual.TextStim(win, pos=[0,+40],text='Consider how the following word describes you while looking at the graph', height=text_height)
    message2 = visual.TextStim(win, pos=[0,-40],text="Press a key when ready.", height=text_height)
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, -1])
    vertices.append([ -feedback_area_width / 2, -1])


    baseline_line_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0
    )

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=0.2)
    peak_alpha_channels = [channels["Oz"],
                              channels["PO3"],
                              channels["PO4"]]

    baseline_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]

    full_eeg = [[] for i in range(len(channels))]
    full_eeg_no_artifacts = [[] for i in range(len(channels))]
    events = []
    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length/60))

    for frameN in range(priming_length):
        chunk, timestamps = inlet.pull_chunk()



        if 0 <= frameN < fixation_length:  # present fixation for a subset of frames
            fixation.draw()
        if fixation_length <= frameN < stimulus_length + fixation_length:
            if frameN == fixation_length + 1:
                events.append(EEGEvent("priming_stimulus", trialClock.getTime(), priming_stimulus))
            visual.TextStim(win, pos=[0, 0], text=priming_stimulus, height=text_height).draw()  # trait-adjective

        if fixation_length + stimulus_length <= frameN < priming_length + fixation_length:  # present stim for a different subset
            for sample in chunk:  # put new samples in the eeg buffer
                frontal_samples = [sample[i] for i in baseline_channels]
                if max(frontal_samples) > 80:
                    events.append(EEGEvent("eye_blink_artifact", 0, 1))
                    artifact_length_remaining = 25

                if artifact_length_remaining == 0:
                    for index, channel_data in enumerate(sample):
                        full_eeg_no_artifacts[index].append(channel_data)
                else:
                    artifact_length_remaining -= 1

                for index, channel_data in enumerate(sample):
                    full_eeg[index].append(channel_data)

            if frameN % frames_per_bar == 0:
                bars += 1
            stimuli_to_show = feedback_stimuli[:bars]
            for stimulus in stimuli_to_show:
                stimulus.draw()
            baseline_line_stimulus.draw()

        win.flip()

    frontal_eeg = [full_eeg[i] for i in baseline_channels]
    last_eeg = map(lambda channel: channel[len(channel)-125:], frontal_eeg)

    peak_alpha = np.mean(map(lambda samples: individual_peak_alpha(samples), [full_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg[i] for i in baseline_channels]))

    return baseline_frontal_alpha_power, peak_alpha, full_eeg, events

def show_no_feedback(win, inlet, outlet, priming_stimulus, ipaf):

    message1 = visual.TextStim(win, pos=[0, +20], text='Perform the meditation practice while keeping your eyes focused on the dot in the center of the screen', height=text_height)
    message2 = visual.TextStim(win, pos=[0, -20], text="Press a key when ready.", height=text_height)
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)



    full_eeg = [[] for i in range(len(channels))]
    events = []

    # show some priming stimuli while recording baseline data
    meditation_length = 14400
    fixation_length = 60

    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length / 60))
    for frameN in range(meditation_length):
        chunk, timestamps = inlet.pull_chunk()

        for sample in chunk:  # put new samples in the eeg buffer
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if 0 <= frameN < meditation_length:  # present fixation for a subset of frames
            fixation.draw()
        win.flip()

    return full_eeg, events

def show_neurofeedback(win, inlet, outlet, baseline, ipaf):
    import scipy.ndimage.filters as filters
    neurofeedback_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]



    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 60
    smoothing_window_size = 30
    neurofeedback_length = 5400 # 1.5 minutes
    # neurofeedback_length = 600
    fixation_length = 120
    artifact_length_remaining = 0

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, -1])
    vertices.append([ -feedback_area_width / 2, -1])


    baseline_line_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0
    )

    events.append(EEGEvent("fixation", 0, fixation_length/60))
    trialClock = core.Clock()

    for frameN in range(neurofeedback_length + fixation_length):
        chunk, timestamp = inlet.pull_chunk()
        if len(neurofeedback_eeg_buffer[0]) + len(chunk) >= sample_rate:  # more than 1 second worth of samples in the buffer
            for index, channel in enumerate(neurofeedback_eeg_buffer):
                neurofeedback_eeg_buffer[index] = channel[len(chunk):] #take chunk size of samples out of buffer

        for sample in chunk: #put new samples in the eeg buffer
            for index, channel in enumerate(neurofeedback_channels):
                neurofeedback_eeg_buffer[index].append(sample[channel])
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if fixation_length <= frameN < neurofeedback_length + fixation_length:
            buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), neurofeedback_eeg_buffer)
            alpha_power = np.mean(buffer_alpha_powers)
            if artifact_length_remaining == 0:
                if alpha_power >= baseline * 2.5 and len(alpha_powers) > 0:  # eye-blink artifact, so just ignore
                    print("eye blink")
                    alpha_powers.append(alpha_powers[-1])
                    artifact_length_remaining = 60
                    events.append(EEGEvent("eyeblink_artifact", trialClock.getTime(), alpha_power))
                else:
                    alpha_powers.append(alpha_power)
            else:
                artifact_length_remaining -= 1
                alpha_powers.append(alpha_powers[-1])

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                smoothed_alpha_powers = filters.gaussian_filter1d(alpha_powers[len(alpha_powers) - smoothing_window_size:], 1)
                neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers)/2] / baseline) - 1) * 100 # smoothed
                # neurofeedback_value = ((alpha_powers[-1] / baseline) - 1) * 100 #unsmoothed

                bar = ((frameN - 120) / frames_per_bar)  # the nth bar of the feedback
                total_bars = ((neurofeedback_length - 120) / frames_per_bar)
                feedback_area_width = (window_x - window_x / 10)
                bar_width = feedback_area_width / total_bars

                vertices = []
                vertices.append([bar * bar_width - feedback_area_width / 2, 0])
                vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, 0])
                vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, neurofeedback_value])
                vertices.append([bar * bar_width - feedback_area_width / 2, neurofeedback_value])

                neurofeedback_values.append(neurofeedback_value)
                neurofeedback_stimulus = visual.ShapeStim(
                    win=win,
                    vertices=vertices,
                    closeShape=True,
                    fillColor="white"
                )
                neurofeedback_stimuli.append(neurofeedback_stimulus)
                events.append(EEGEvent("neurofeedback_new_bar", trialClock.getTime(), neurofeedback_value))

            for stimulus in neurofeedback_stimuli:
                stimulus.draw()
            baseline_line_stimulus.draw()

        win.flip()

    return full_eeg, events, neurofeedback_stimuli, neurofeedback_values

def show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf):
    neurofeedback_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]


    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []
    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 60
    smoothing_window_size = 30
    neurofeedback_length = 5400

    fixation_length = 120
    events.append(EEGEvent("fixation", 0, fixation_length/60))

    for frameN in range(neurofeedback_length + fixation_length):
        chunk, timestamp = inlet.pull_chunk()
        if len(neurofeedback_eeg_buffer[0]) + len(
                chunk) >= sample_rate:  # more than 1 second worth of samples in the buffer
            for index, channel in enumerate(neurofeedback_eeg_buffer):
                neurofeedback_eeg_buffer[index] = channel[len(chunk):]  # take chunk size of samples out of buffer

        for sample in chunk:  # put new samples in the eeg buffer
            for index, channel in enumerate(neurofeedback_channels):
                neurofeedback_eeg_buffer[index].append(sample[channel])
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if 0 <= frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if fixation_length <= frameN < neurofeedback_length:
            buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), neurofeedback_eeg_buffer)
            alpha_power = np.mean(buffer_alpha_powers)
            alpha_powers.append(alpha_power)

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                smoothed_alpha_powers = filters.gaussian_filter1d(
                    alpha_powers[len(alpha_powers) - smoothing_window_size:], 1)
                neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers)/2] / baseline) - 1) * 100
                # neurofeedback_value = smoothed_alpha_powers[len(smoothed_alpha_powers) / 2] - baseline

                bar = ((frameN - fixation_length) / frames_per_bar)  # the nth bar of the feedback
                total_bars = ((neurofeedback_length - fixation_length) / frames_per_bar)
                feedback_area_width = (window_x - window_x / 10)
                bar_width = feedback_area_width / total_bars

                vertices = []
                vertices.append([bar * bar_width - feedback_area_width / 2, 0])
                vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, 0])
                vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, neurofeedback_value])
                vertices.append([bar * bar_width - feedback_area_width / 2, neurofeedback_value])

                neurofeedback_values.append(neurofeedback_value * 0.1)
                neurofeedback_stimulus = visual.ShapeStim(
                    win=win,
                    vertices=vertices,
                    closeShape=True,
                    fillColor="white"
                )
                neurofeedback_stimuli.append(neurofeedback_stimulus)
        fixation.draw()

        win.flip()
    return full_eeg, events, neurofeedback_stimuli, neurofeedback_values

def show_neurofeedback_free_play(win, inlet, outlet, baseline, ipaf):
    neurofeedback_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]


    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    neurofeedback_stimuli = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 60
    smoothing_window_size = 30
    neurofeedback_length = 25200  # 7 minutes
    visible_neurofeedback_length = 1200
    fixation_length = 120

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, -1])
    vertices.append([ -feedback_area_width / 2, -1])


    baseline_line_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0
    )

    events.append(EEGEvent("fixation", 0, fixation_length / 60))

    trialClock = core.Clock()
    message = visual.TextStim(win, pos=(-window_x/2 +50, window_y/2 - 50), text = '[Esc] to quit', color = 'white', alignHoriz = 'left', alignVert = 'bottom', height=text_height)


    trialClock = core.Clock()
    lastFPS = 1

    print(win.fps())
    t = lastFPSupdate = 0

    win.setRecordFrameIntervals(True)

    for frameN in range(neurofeedback_length):
        # t = trialClock.getTime()
        # if t - lastFPSupdate > 1.0:
        #     lastFPS = win.fps()
        #     lastFPSupdate = t
        # message.text = "%ifps, [Esc] to quit" % lastFPS
        # message.draw()

        chunk, timestamp = inlet.pull_chunk()
        if len(neurofeedback_eeg_buffer[0]) + len(chunk) >= sample_rate:  # more than 1 second worth of samples in the buffer
            for index, channel in enumerate(neurofeedback_eeg_buffer):
                neurofeedback_eeg_buffer[index] = channel[len(chunk):]  # take chunk size of samples out of buffer

        for sample in chunk:  # put new samples in the eeg buffer
            for index, channel in enumerate(neurofeedback_channels):
                neurofeedback_eeg_buffer[index].append(sample[channel])
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if fixation_length <= frameN < neurofeedback_length + fixation_length:
            buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), neurofeedback_eeg_buffer)
            alpha_power = np.mean(buffer_alpha_powers)
            alpha_powers.append(alpha_power)

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                smoothed_alpha_powers = filters.gaussian_filter1d(
                    alpha_powers[len(alpha_powers) - smoothing_window_size:], 1)
                neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers)/2] / baseline) - 1) * 100
                # neurofeedback_value = smoothed_alpha_powers[len(smoothed_alpha_powers) / 2] - baseline

                total_bars = ((visible_neurofeedback_length - 120) / frames_per_bar)
                feedback_area_width = (window_x - window_x / 10)
                bar_width = feedback_area_width / total_bars

                vertices = []
                vertices.append([(feedback_area_width / 2) - bar_width, 0])
                vertices.append([(feedback_area_width / 2) + bar_width, 0])
                vertices.append([(feedback_area_width / 2) + bar_width, neurofeedback_value])
                vertices.append([(feedback_area_width / 2) - bar_width, neurofeedback_value])

                neurofeedback_stimulus = visual.ShapeStim(
                    win=win,
                    vertices=vertices,
                    closeShape=True,
                    fillColor="white"
                )

                for index, stimulus in enumerate(neurofeedback_stimuli): # shift all existing stimuli to the left
                    neurofeedback_stimuli[index].vertices = map(lambda vertices: [vertices[0] - bar_width, vertices[1]], stimulus.vertices)
                if len(neurofeedback_stimuli) == total_bars: # pop off the first bar (leftmost)
                    neurofeedback_stimuli = neurofeedback_stimuli[1:]
                neurofeedback_stimuli.append(neurofeedback_stimulus)
                events.append(EEGEvent("neurofeedback_new_bar", trialClock.getTime(), neurofeedback_value))

            for stimulus in neurofeedback_stimuli:
                stimulus.draw()
            baseline_line_stimulus.draw()

        win.flip()

    return full_eeg, events

def show_sham_feedback(win, inlet, outlet, stimuli, neurofeedback_length):

    frames_per_bar = 60
    smoothing_window_size = 30
    fixation_length = 120
    full_eeg = [[] for i in range(len(channels))]
    events = []
    trialClock = core.Clock()

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, -1])
    vertices.append([ -feedback_area_width / 2, -1])


    baseline_line_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0
    )

    visible_stimuli = 0

    for frameN in range(neurofeedback_length + fixation_length):
        chunk, timestamp = inlet.pull_chunk()

        for sample in chunk:  # put new samples in the eeg buffer
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if fixation_length <= frameN < neurofeedback_length + fixation_length:
            if frameN % 10 == 0:
                visible_stimuli += 1
            for stimulus in stimuli[:visible_stimuli]:
                stimulus.draw()
            baseline_line_stimulus.draw()

        win.flip()

    return full_eeg, events, stimuli

def show_meditation_only_questions(win, subject_id, set, run):
    answers = []
    effortless_awareness_question = visual.TextStim(win,
                                                    pos=[0, 250],
                                                    text="How effortless was your awareness overall during the previous meditation session?", height=text_height)
    effortless_awareness_scale = visual.RatingScale(win,pos=[0, 120], low=0, high=10,labels=["Not at all effortless", "Extremely effortless"], scale=None)

    while effortless_awareness_scale.noResponse:
        effortless_awareness_question.draw()
        effortless_awareness_scale.draw()
        win.flip()
    answers.append(effortless_awareness_scale.getRating())

    win.flip()

    import csv

    path = "experiment_data/subject_{0}/set_{1}/run_{2}".format(subject_id, set, run, type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    with open('experiment_data/subject_{0}/set_{1}/run_{2}/questions.csv'.format(subject_id, set, run, type), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["question", "value"]) # header row
        for index, answer in enumerate(answers):
            writer.writerow([index, answer])

def show_run_feedback_questions(win, neurofeedback_stimuli, neurofeedback_values, subject_id, set, run):

    answers = []

    neurofeedback_max = max(neurofeedback_values)
    neurofeedback_min = min(neurofeedback_values)
    scaling = 100/max(max(neurofeedback_max, 0), abs(min(neurofeedback_min, 0)))
    for stimulus in neurofeedback_stimuli: # shift and scale all existing stimuli to the down to make room for questions
        stimulus.size *= (1, scaling)
        stimulus.pos += (0, -200)

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, -199])
    vertices.append([feedback_area_width / 2, -199])
    vertices.append([feedback_area_width / 2, -201])
    vertices.append([ -feedback_area_width / 2, -201])


    baseline_line_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0
    )

    feedback_direction_question = visual.TextStim(win,
                                                  pos=[0, 350],
                                                  text="Did increases in your experience as being effortlessly aware correspond to the graph increasing or decreasing?", height=text_height)
    feedback_direction_scale = visual.RatingScale(win,
                                                  pos=[0, 220],
                                                  choices=['Increasing', 'Decreasing'])

    while feedback_direction_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        baseline_line_stimulus.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())

    feedback_direction_confidence_question = visual.TextStim(win,
                               pos=[0, 350],
                               text="How confident are you that effortless awareness corresponds with the graph {}?".format(feedback_direction_scale.getRating().lower()), height=text_height)
    feedback_direction_confidence_scale = visual.RatingScale(win,
                                                  low=0,
                                                  high=10,
                                                  labels=["Not at all", "Perfectly"],
                                                  scale=None,
                                                  pos=[0, 220])

    while feedback_direction_confidence_scale.noResponse:
        feedback_direction_confidence_question.draw()
        feedback_direction_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        baseline_line_stimulus.draw()
        win.flip()
    answers.append(feedback_direction_confidence_scale.getRating())


    feedback_baseline_question = visual.TextStim(win,
                            pos=[0, 350],
                            text="Did the graph being above or below the green line correspond with your experience being one of being effortless aware?", height=text_height)
    feedback_baseline_scale = visual.RatingScale(win,
                                     pos=[0, 220],
                                     choices=['Above', 'Below'])

    while feedback_baseline_scale.noResponse:
        feedback_baseline_question.draw()
        feedback_baseline_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        baseline_line_stimulus.draw()
        win.flip()
    answers.append(feedback_baseline_scale.getRating())

    feedback_baseline_confidence_question = visual.TextStim(win,
                                                pos=[0, 350],
                                                text="How confident are you that effortless awareness corresponds with the graph being {} the green line?".format(feedback_baseline_scale.getRating().lower()),
                                                height = text_height)
    feedback_baseline_confidence_scale = visual.RatingScale(win,
                                                  low=0,
                                                  high=10,
                                                  labels=["Not at all", "Perfectly"],
                                                  scale=None,
                                                  pos=[0, 220])

    while feedback_baseline_confidence_scale.noResponse:
        feedback_baseline_confidence_question.draw()
        feedback_baseline_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        baseline_line_stimulus.draw()
        win.flip()
    answers.append(feedback_baseline_confidence_scale.getRating())

    effortless_awareness_question = visual.TextStim(win,
                                                    pos=[0, 350],
                                                    text="How effortless was your awareness overall during the previous meditation session?",
                                                    height = text_height)
    effortless_awareness_scale = visual.RatingScale(win,pos=[0, 220], low=0, high=10,labels=["Not at all effortless", "Extremely effortless"], scale=None)

    while effortless_awareness_scale.noResponse:
        effortless_awareness_question.draw()
        effortless_awareness_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        baseline_line_stimulus.draw()
        win.flip()
    answers.append(effortless_awareness_scale.getRating())

    win.flip()

    import csv

    path = "experiment_data/subject_{0}/set_{1}/run_{2}".format(subject_id, set, run, type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    with open('experiment_data/subject_{0}/set_{1}/run_{2}/questions.csv'.format(subject_id, set, run, type), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["question", "value"]) # header row
        for index, answer in enumerate(answers):
            writer.writerow([index, answer])

def show_final_feedback_questions(win, subject_id, set, run):
    answers = []
    feedback_direction_question = visual.TextStim(win,
                            pos=[0, 20],
                            text="Across all experiments so far, do you think effortless awareness corresponds with the graph being upward or downward?",
                            height=text_height)
    feedback_direction_scale = visual.RatingScale(win,
                                     choices=['Upward', 'Downward'])
    while feedback_direction_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())

    feedback_direction_confidence_question = visual.TextStim(win,
                                                    pos=[0, 250],
                                                    text="How well does the graph correspond with your experience during effortless awareness and its opposite?",
                                                    height=text_height)
    feedback_direction_confidence_scale = visual.RatingScale(win,pos=[0, 120], low=0, high=10,labels=["Not at all", "Perfectly"], scale=None)

    while feedback_direction_confidence_scale.noResponse:
        feedback_direction_confidence_question.draw()
        feedback_direction_confidence_scale.draw()
        win.flip()

    answers.append(feedback_direction_confidence_scale.getRating())

    path = "experiment_data/subject_{0}/set_{1}/run_{2}".format(subject_id, set, run, type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    import csv

    with open('experiment_data/subject_{0}/set_{1}/questions_final.csv'.format(subject_id, set, run, type), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["question", "value"]) # header row
        for index, answer in enumerate(answers):
            writer.writerow([index, answer])

def individual_peak_alpha(samples):
    ps = np.abs(np.fft.fft(samples)) ** 2  # power spectrum

    time_step = 1.0 / sample_rate
    freqs = np.fft.fftfreq(len(samples), time_step)
    idx = np.argsort(freqs)

    peak_alpha = 0.0
    total_power = 0
    for freq, power in zip(freqs[idx], ps[idx]):
        if freq >= 7.5 and freq <= 12.5:
            peak_alpha += freq * power
            total_power += power

    return peak_alpha / total_power

def eeg_power(samples, ipaf):
    f, Pxx = scipy.signal.periodogram(samples, fs=sample_rate)
    ind_min = scipy.argmax(f > ipaf - 2.5)
    ind_max = scipy.argmax(f > ipaf + 2.5)
    return scipy.trapz(Pxx[ind_min: ind_max], f[ind_min: ind_max])

def baseline_feedback(win, priming_length, baseline):
    from random import random as rand

    feedback_signal = [[] for i in range(len(channels))]

    i = 1.0
    while i < ((priming_length/60)*sample_rate + sample_rate):
        alpha = np.sin(2 * np.pi * 10 * (i / sample_rate)) * 20
        beta = np.sin(2 * np.pi * 20 * (i / sample_rate)) * 5
        delta = np.sin(2 * np.pi * 2 * (i / sample_rate)) * 10
        gamma = np.sin(2 * np.pi * 35 * (i / sample_rate)) * 4
        theta = np.sin(2 * np.pi * 6 * (i / sample_rate)) * 3

        for channel in feedback_signal:
            channel.append(rand()* 40 - 20 + alpha + beta + delta + gamma + theta)

        i += 1

    feedback_stimuli = []
    alpha_powers = []
    ipaf = 10
    frames_per_bar = 60
    smoothing_window_size = 30

    # just do it sort of like the live version
    for frame in range(priming_length):
        buffer = map(lambda channel: channel[int(round(frame * (sample_rate/60))):int(round((frame + 60) * (sample_rate/60)))], feedback_signal)
        # buffer = map(lambda channel: channel[frame*sample_rate:int(((frame + 60)/60)*sample_rate)], feedback_signal)

        buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), buffer)
        alpha_power = np.mean(buffer_alpha_powers)
        alpha_powers.append(alpha_power)
        if frame % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
            # use gaussian smoothed alpha power to determine neurofeedback value
            smoothed_alpha_powers = filters.gaussian_filter1d(alpha_powers[len(alpha_powers) - smoothing_window_size:],
                                                              1)
            neurofeedback_value = ((smoothed_alpha_powers[
                                        len(smoothed_alpha_powers) / 2] / baseline) - 1) * 400  # smoothed

            bar = (frame / frames_per_bar)  # the nth bar of the feedback
            total_bars = (priming_length / frames_per_bar)
            feedback_area_width = (window_x - window_x / 10)
            bar_width = feedback_area_width / total_bars

            vertices = []
            vertices.append([bar * bar_width - feedback_area_width / 2, 0])
            vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, 0])
            vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, neurofeedback_value])
            vertices.append([bar * bar_width - feedback_area_width / 2, neurofeedback_value])

            neurofeedback_stimulus = visual.ShapeStim(
                win=win,
                vertices=vertices,
                closeShape=True,
                fillColor="white"
            )
            feedback_stimuli.append(neurofeedback_stimulus)

    return feedback_stimuli

def stimuli_from_eeg(win, subject_id, set, run):
    baseline_path = "experiment_data/subject_{0}/set_{1}/run_{2}/baseline/eeg.edf".format(subject_id - 1, set, run, type)
    f = pyedflib.EdfReader(baseline_path)
    n = f.signals_in_file
    signal_labels = f.getSignalLabels()
    baseline_eeg = np.zeros((n, f.getNSamples()[0]))
    for i in np.arange(n):
        baseline_eeg[i, :] = f.readSignal(i)

    peak_alpha_channels = [channels["Oz"],
                              channels["PO3"],
                              channels["PO4"]]

    baseline_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]

    ipaf = np.mean(map(lambda samples: individual_peak_alpha(samples), [baseline_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, ipaf), [baseline_eeg[i] for i in baseline_channels]))

    baseline_path = "experiment_data/subject_{0}/set_{1}/run_{2}/trial/eeg.edf".format(subject_id, set, run, type)
    f = pyedflib.EdfReader(baseline_path)
    n = f.signals_in_file
    signal_labels = f.getSignalLabels()
    trial_sham_eeg = np.zeros((n, f.getNSamples()[0]))
    for i in np.arange(n):
        trial_sham_eeg[i, :] = f.readSignal(i)


    feedback_stimuli = []
    feedback_values = []
    alpha_powers = []
    frames_per_bar = 60
    smoothing_window_size = 30
    feedback_length = (trial_sham_eeg / 125) * 60

    # just do it sort of like the live versions
    for frame in range(feedback_length):

        buffer = map(lambda channel: channel[round(frame * (sample_rate/60)):round((frame + 60) * (sample_rate/60))], [trial_sham_eeg[i] for i in baseline_channels])

        buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), buffer)
        alpha_power = np.mean(buffer_alpha_powers)
        alpha_powers.append(alpha_power)
        if frame % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
            # use gaussian smoothed alpha power to determine neurofeedback value
            smoothed_alpha_powers = filters.gaussian_filter1d(alpha_powers[len(alpha_powers) - smoothing_window_size:],
                                                              1)
            neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers) / 2] / baseline_frontal_alpha_power) - 1) * 100  # smoothed

            bar = (frame / frames_per_bar)  # the nth bar of the feedback
            total_bars = (feedback_length / frames_per_bar)
            feedback_area_width = (window_x - window_x / 10)
            bar_width = feedback_area_width / total_bars

            vertices = []
            vertices.append([bar * bar_width - feedback_area_width / 2, 0])
            vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, 0])
            vertices.append([bar * bar_width + bar_width - feedback_area_width / 2, neurofeedback_value])
            vertices.append([bar * bar_width - feedback_area_width / 2, neurofeedback_value])

            neurofeedback_stimulus = visual.ShapeStim(
                win=win,
                vertices=vertices,
                closeShape=True,
                fillColor="white"
            )
            feedback_stimuli.append(neurofeedback_stimulus)
            feedback_values.append(neurofeedback_value)

    return feedback_stimuli, feedback_values

def connect_to_EEG():
    # first resolve an EEG stream on the lab network
    print("looking for an EEG stream...")
    stream_bp_filtered = resolve_stream('name', 'OpenViBE Stream - Band Pass Filtered')
    # streams = resolve_stream('type', 'EEG')
    print("EEG stream connected")
    # create a new inlet to read from the stream
    inlet = StreamInlet(stream_bp_filtered[0])


    # make an outlet stream for markers
    print("Creating an outlet stream for markers")
    info = StreamInfo('MyMarkerStream', 'Markers', 1, 0, 'string', 'myuidw43536')
    print("Marker stream created")
    # next make an outlet
    outlet = StreamOutlet(info)
    return inlet, outlet

def read_priming_stimuli():
    import csv
    with open('priming_stimuli.csv', 'rb') as f:
        reader = csv.reader(f)
        priming_stimuli = list(reader)

    import random
    random.shuffle(priming_stimuli)
    return priming_stimuli

def save_edf(data, events, subject_id, set, run, type):
    path = "experiment_data/subject_{0}/set_{1}/run_{2}/{3}".format(subject_id, set, run, type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    test_data_file = 'experiment_data/subject_{0}/set_{1}/run_{2}/{3}/eeg.edf'.format(subject_id, set, run, type)
    f = pyedflib.EdfWriter(test_data_file, 16, file_type=pyedflib.FILETYPE_EDFPLUS)

    # set header info
    channel_info = []
    for index, channel in enumerate(data):
        channel_dict = {'label': index2channel[index],
                        'dimension': 'uV',
                        'sample_rate': sample_rate,
                        'physical_max': 100,
                        'physical_min': -100,
                        'digital_max': 32767,
                        'digital_min': -32768,
                        'transducer': '',
                        'prefilter':''}
        channel_info.append(channel_dict)

    f.setSignalHeaders(channel_info)
    # write channel data
    f.writeSamples(np.asarray(data))
    f.close()
    del f

    import csv

    with open('experiment_data/subject_{0}/set_{1}/run_{2}/{3}/events.csv'.format(subject_id, set, run, type), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Latency", "Type", "Value"]) # header row
        for event in events:
            writer.writerow([event.latency, event.type, event.value])

class EEGEvent:
    latency = 0.0
    type = ""
    value = ""

    def __init__(self, type, latency, value):
        self.type = type
        self.latency = latency
        self.value = value

main()