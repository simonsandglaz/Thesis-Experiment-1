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
frames_per_bar = 30 # how many frames per feedback update
window_x = 3840
window_y = 2160

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

neurofeedback_channels = [channels["Fp1"],
                          channels["Fp2"],
                          channels["Fpz"],
                          channels["AF3"],
                          channels["AF4"],
                          channels["Fz"]]

baseline_channels = [channels["Fp1"],
                     channels["Fp2"],
                     channels["Fpz"],
                     channels["AF3"],
                     channels["AF4"],
                     channels["Fz"]]

peak_alpha_channels = [channels["Oz"],
                       channels["PO3"],
                       channels["PO4"]]

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
#   Again, participants are not instructed on a particular strategy for doing this, in the same way as 5) (3 runs, 1.5 minutes each)

subject_id = 1

def main():
    try:  # try to get a previous parameters file
        expInfo = fromFile('lastParams.test')
    except:  # if not there then use a default set
        expInfo = {'observer': 'Simon', 'subject_id': 0}
    expInfo['dateStr'] = data.getDateStr()  # add the current time
    expInfo['subject_id'] = expInfo['subject_id'] + 1

    # present a dialogue to change params
    group = expInfo["group"]
    expInfo["group"] = None
    dlg = gui.DlgFromDict(expInfo, title='Thesis Experiment 1', fixed=['dateStr'])
    if dlg.OK:
        if expInfo['group'] == None:
            print('group is none')
            if "group" in expInfo.keys() and group == "sham":
                expInfo["group"] = "experiment"
            else:
                expInfo["group"] = "sham"

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

    participant_info = {'age': '', 'handedness': '', 'gender': '', 'sex': ''}

    dlg = gui.DlgFromDict(participant_info, title='Psychology Study')
    if dlg.OK:
        print(participant_info)
    else:
        core.quit()  # the user hit cancel so exit

    participant_info['dateStr'] = data.getDateStr()  # add the current time
    participant_info['group'] = expInfo["group"]
    save_participant_details(participant_info, subject_id)

    further_instructions(win, 1)

    # 1. Meditation without feedback (2 runs, 4 minutes each)
    for i in range(2):
        baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        win.flip()
        save_edf(eeg, events, subject_id, 0, i, 'baseline')

        message1 = visual.TextStim(win, pos=[0, +50],
                                   text='Perform the meditation practice while keeping your eyes focused on the dot in the center of the screen',
                                   height=text_height)
        message2 = visual.TextStim(win, pos=[0, -20], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        eeg, events = show_no_feedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 0, i, 'trial')

        show_meditation_only_questions(win, subject_id, 0, i)
        stimuli_index += 1

    further_instructions(win, 2)
    # 2. Meditation with offline feedback (feedback graph shown offline after each run; 4 runs, 1.5 minutes each)
    for i in range(4):
        baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        win.flip()
        save_edf(eeg, events, subject_id, 1, i, 'baseline')

        message1 = visual.TextStim(win, pos=[0, +40], text='Please perform the instructed attention practice', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        eeg, events, feedback_stimuli, feedback_values = show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf)
        if expInfo["group"] == "sham":
            feedback_values = feedback_values_from_eeg(subject_id, 1, i)
            feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values, 5400, (
                (5400 - 90) / frames_per_bar))
        save_edf(eeg, events, subject_id, 1, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 1, i)
        if i == 4:
            show_final_feedback_questions(win, 1, i)
        stimuli_index += 1

    further_instructions(win, 3)
    # 3. Meditation with real-time feedback (4 runs, 1.5 minutes each)
    for i in range(4):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        win.flip()
        save_edf(eeg, events, subject_id, 2, i, 'baseline')

        if expInfo["group"] == "sham":
            sham_values = feedback_values_from_eeg(subject_id, 2, i)

        message1 = visual.TextStim(win, pos=[0, +40], text='Please perform the instructed attention practice', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        if expInfo["group"] == "sham":
            eeg, events, feedback_stimuli, feedback_values = show_sham_feedback(win, inlet, outlet, sham_values)
        else:
            eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 2, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 4:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    further_instructions(win, 4)
    # 4. "Free-play" session. Participants are allowed to experiment with the feedback, using strategies of their own choosing. (2 runs, 7 minutes each).
    for i in range(2):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        win.flip()
        save_edf(eeg, events, subject_id, 3, i, 'baseline')
        if expInfo["group"] == "sham":
            sham_values = feedback_values_from_eeg(subject_id, 3, i)

        message1 = visual.TextStim(win, pos=[0, +40], text='Experiment with methods to manipulate the graph', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()
        if expInfo["group"] == "sham":
            eeg, events = show_sham_neurofeedback_free_play(win, inlet, outlet, sham_values)
        else:
            eeg, events = show_neurofeedback_free_play(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 3, i, 'trial')
        stimuli_index += 1

    further_instructions(win, 5)
    # 5. Volitional control in direction of effortless awareness
    for i in range(3):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 4, i, 'baseline')

        win.flip()
        if expInfo["group"] == "sham":
            sham_values = feedback_values_from_eeg(subject_id, 4, i)

        message1 = visual.TextStim(win, pos=[0, +50], text='Please try to make the graph go in the direction that you think corresponds to increased effortlessness of awareness', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        if expInfo["group"] == "sham":
            eeg, events, feedback_stimuli, feedback_values = show_sham_feedback(win, inlet, outlet, sham_values)
        else:
            eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 4, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 3:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    further_instructions(win, 6)
    # 6. Volitional control in direction of opposite effortless awareness
    for i in range(3):
        baseline, ipaf, eeg, events = show_baseline_with_graph(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        win.flip()
        save_edf(eeg, events, subject_id, 5, i, 'baseline')

        if expInfo["group"] == "sham":
            sham_values = feedback_values_from_eeg(subject_id, 5, i)


        message1 = visual.TextStim(win, pos=[0, +50], text='Please try to make the graph go in the direction that you think corresponds to decreased effortlessness of awareness', height=text_height)
        message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
        message1.draw()
        message2.draw()
        win.flip()
        event.waitKeys()

        if expInfo["group"] == "sham":
            eeg, events, feedback_stimuli, feedback_values = show_sham_feedback(win, inlet, outlet, sham_values)
        else:
            eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)

        save_edf(eeg, events, subject_id, 5, i, 'trial')
        show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
        if i == 3:
            show_final_feedback_questions(win, subject_id, 2, i)
        stimuli_index += 1

    thank_you_message(win)

    win.close()
    core.quit()

def show_baseline(win, inlet, outlet, priming_stimulus):

    # show some priming stimuli while recording baseline data
    priming_length = 1200 # 20 seconds
    fixation_length = 60 # 1 second
    stimulus_length = 180 # 3 seconds
    artifact_length_remaining = 0
    bars = 0

    message1 = visual.TextStim(win, pos=[0,+40],text='Consider how the following word describes you', height=text_height)
    message2 = visual.TextStim(win, pos=[0,-40],text="Press a key when ready.", height=text_height)
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    outlet.push_sample(['baseline_start'])

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    full_eeg = [[] for i in range(len(channels))]
    full_eeg_no_artifacts = [[] for i in range(len(channels))]

    events = []

    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length/60))
    for frameN in range(priming_length + fixation_length + stimulus_length):
        chunk, timestamps = inlet.pull_chunk()

        if 0 <= frameN < fixation_length:  # present fixation for a subset of frames
            fixation.draw()
        if fixation_length <= frameN < stimulus_length + fixation_length:
            if frameN == fixation_length + 1:
                events.append(EEGEvent("priming_stimulus", trialClock.getTime(), priming_stimulus))
            visual.TextStim(win, pos=[0, 0], text=priming_stimulus, height=text_height).draw()  # trait-adjective

        if fixation_length + stimulus_length <= frameN < priming_length + fixation_length + stimulus_length:  # present stim for a different subset
            for sample in chunk:  # put new samples in the eeg buffer
                frontal_samples = [sample[i] for i in baseline_channels]
                if max(frontal_samples) > 80:
                    events.append(EEGEvent("eye_blink_artifact", 0, 1))
                    artifact_length_remaining = 25
                    # print("eye blink")

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
    # priming_length = 240
    priming_length = 1200 # 20 seconds
    fixation_length = 60 # 1 second
    stimulus_length = 180 # 3 seconds
    artifact_length_remaining = 0
    bars = 0

    feedback_values = baseline_feedback(win, priming_length, 190)

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


    line = baseline_line_stimulus(win)

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    full_eeg = [[] for i in range(len(channels))]
    full_eeg_no_artifacts = [[] for i in range(len(channels))]
    events = []
    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length/60))

    trialClock = core.Clock()
    lastFPS = 1
    message = visual.TextStim(win, pos=(-window_x/2 +50, window_y/2 - 50), text = '[Esc] to quit', color = 'white', alignHoriz = 'left', alignVert = 'bottom', height=text_height)

    # print(win.fps())
    t = lastFPSupdate = 0

    win.setRecordFrameIntervals(True)

    feedback_stimuli = []
    for frameN in range(priming_length + fixation_length + stimulus_length):
        chunk, timestamps = inlet.pull_chunk()

        if 0 <= frameN < fixation_length:  # present fixation for a subset of frames
            fixation.draw()
        if fixation_length <= frameN < stimulus_length + fixation_length:
            if frameN == fixation_length + 1:
                events.append(EEGEvent("priming_stimulus", trialClock.getTime(), priming_stimulus))
            visual.TextStim(win, pos=[0, 0], text=priming_stimulus, height=text_height).draw()  # trait-adjective

        if fixation_length + stimulus_length <= frameN <= priming_length + fixation_length + stimulus_length:  # present stim for a different subset
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
                bar = ((frameN - fixation_length - stimulus_length) / frames_per_bar) + 1  # the nth bar of the feedback
                feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values[:bar], priming_length, bar - 1)

            for stimulus in feedback_stimuli:
                stimulus.draw()

            line.draw()
        # t = trialClock.getTime()
        # if t - lastFPSupdate > 1.0:
        #     lastFPS = win.fps()
        #     lastFPSupdate = t
        # message.text = "%ifps, [Esc] to quit" % lastFPS
        # message.draw()

        win.flip()

    frontal_eeg = [full_eeg[i] for i in baseline_channels]
    last_eeg = map(lambda channel: channel[len(channel)-125:], frontal_eeg)

    peak_alpha = np.mean(map(lambda samples: individual_peak_alpha(samples), [full_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg[i] for i in baseline_channels]))

    return baseline_frontal_alpha_power, peak_alpha, full_eeg, events

def show_no_feedback(win, inlet, outlet, priming_stimulus, ipaf):
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
    neurofeedback_length = 5400 # 1.5 minutes
    fixation_length = 120

    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    message = visual.TextStim(win, pos=(-window_x/2 +50, window_y/2 - 50), text = '[Esc] to quit', color = 'white', alignHoriz = 'left', alignVert = 'bottom', height=text_height)

    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    line = baseline_line_stimulus(win)
    events.append(EEGEvent("fixation", 0, fixation_length/60))
    # trialClock = core.Clock()
    # lastFPS = 1
    #
    # print(win.fps())
    # t = lastFPSupdate = 0
    #
    # win.setRecordFrameIntervals(True)

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
            alpha_powers.append(alpha_power)

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                neurofeedback_values.append(neurofeedback_value(alpha_powers, baseline))
                bar = ((frameN - fixation_length) / frames_per_bar)  # the nth bar of the feedback
                neurofeedback_stimuli = stimuli_from_neurofeedback_values(win, neurofeedback_values, neurofeedback_length, bar)

            for stimulus in neurofeedback_stimuli:
                stimulus.draw()
            line.draw()
            # t = trialClock.getTime()
            # if t - lastFPSupdate > 1.0:
            #     lastFPS = win.fps()
            #     lastFPSupdate = t
            # message.text = "%ifps, [Esc] to quit" % lastFPS
            # message.draw()

        win.flip()

    return full_eeg, events, neurofeedback_stimuli, neurofeedback_values

def show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf):
    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []
    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

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
                neurofeedback_values.append(neurofeedback_value(alpha_powers, baseline))
        fixation.draw()

        win.flip()

    feedback_area_width = (window_x - window_x / 10)
    neurofeedback_stimuli = stimuli_from_neurofeedback_values(win, neurofeedback_values, neurofeedback_length, ((neurofeedback_length - fixation_length) / frames_per_bar))
    return full_eeg, events, neurofeedback_stimuli, neurofeedback_values

def show_neurofeedback_free_play(win, inlet, outlet, baseline, ipaf):
    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    neurofeedback_stimuli = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    smoothing_window_size = 30
    neurofeedback_length = 25200  # 7 minutes
    visible_neurofeedback_length = 1200
    fixation_length = 120

    line = baseline_line_stimulus(win)

    events.append(EEGEvent("fixation", 0, fixation_length / 60))

    trialClock = core.Clock()
    lastFPS = 1
    message = visual.TextStim(win, pos=(-window_x/2 +50, window_y/2 - 50), text = '[Esc] to quit', color = 'white', alignHoriz = 'left', alignVert = 'bottom', height=text_height)

    # print(win.fps())
    t = lastFPSupdate = 0

    win.setRecordFrameIntervals(True)


    neurofeedback_values = []
    for frameN in range(neurofeedback_length + fixation_length):
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
                neurofeedback_values.append(neurofeedback_value(alpha_powers, baseline))
                bar = ((frameN - fixation_length) / frames_per_bar)  # the nth bar of the feedback
                total_bars = ((visible_neurofeedback_length) / frames_per_bar)
                if bar >= total_bars:
                    bar = total_bars - 1
                neurofeedback_stimuli = stimuli_from_neurofeedback_values(win, neurofeedback_values[-total_bars:], visible_neurofeedback_length, bar)
                # events.append(EEGEvent("neurofeedback_new_bar", trialClock.getTime(), neurofeedback_value))

            for stimulus in neurofeedback_stimuli:
                stimulus.draw()
            line.draw()

        # t = trialClock.getTime()
        # if t - lastFPSupdate > 1.0:
        #     lastFPS = win.fps()
        #     lastFPSupdate = t
        # message.text = "%ifps, [Esc] to quit" % lastFPS
        # message.draw()


        win.flip()

    return full_eeg, events

def show_sham_neurofeedback_free_play(win, inlet, outlet, feedback_values):
    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    neurofeedback_length = 25200  # 7 minutes
    visible_neurofeedback_length = 1200
    fixation_length = 120

    line = baseline_line_stimulus(win)

    events.append(EEGEvent("fixation", 0, fixation_length / 60))

    trialClock = core.Clock()
    lastFPS = 1
    message = visual.TextStim(win, pos=(-window_x / 2 + 50, window_y / 2 - 50), text='[Esc] to quit', color='white',
                              alignHoriz='left', alignVert='bottom', height=text_height)

    # print(win.fps())
    t = lastFPSupdate = 0

    win.setRecordFrameIntervals(True)

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

        if frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()

        if fixation_length <= frameN < neurofeedback_length + fixation_length:

            if frameN % frames_per_bar == 0:
                bar = ((frameN - fixation_length) / frames_per_bar)  # the nth bar of the feedback
                virtual_bar = bar
                total_bars = ((visible_neurofeedback_length) / frames_per_bar)
                if bar >= total_bars:
                    virtual_bar = total_bars
                    feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values[(bar - total_bars):bar],
                                                                         visible_neurofeedback_length, virtual_bar - 1)
                else:
                    feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values[0:bar],
                                                                         visible_neurofeedback_length, virtual_bar - 1)


                # feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values[-total_bars:], visible_neurofeedback_length, bar)

            for stimulus in feedback_stimuli:
                stimulus.draw()
            line.draw()
            t = trialClock.getTime()
            if t - lastFPSupdate > 1.0:
                lastFPS = win.fps()
                lastFPSupdate = t
            message.text = "%ifps, [Esc] to quit" % lastFPS
            message.draw()
        win.flip()

    return full_eeg, events

def show_sham_feedback(win, inlet, outlet, feedback_values):
    neurofeedback_length = 5400 # 1.5 minutes
    fixation_length = 120
    full_eeg = [[] for i in range(len(channels))]
    events = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    line = baseline_line_stimulus(win)

    feedback_stimuli = []

    for frameN in range(neurofeedback_length + fixation_length):
        chunk, timestamp = inlet.pull_chunk()

        for sample in chunk:  # put new samples in the eeg buffer
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if frameN < fixation_length:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if fixation_length <= frameN < neurofeedback_length + fixation_length:
            if frameN % frames_per_bar == 0:
                bar = ((frameN - fixation_length) / frames_per_bar) + 1  # the nth bar of the feedback
                feedback_stimuli = stimuli_from_neurofeedback_values(win, feedback_values[:bar], neurofeedback_length, bar - 1)

            for stimulus in feedback_stimuli:
                stimulus.draw()
            line.draw()

        win.flip()
    return full_eeg, events, feedback_stimuli, feedback_values

def show_meditation_only_questions(win, subject_id, set, run):
    answers = []
    effortless_awareness_question = visual.TextStim(win,
                                                    pos=[0, 250],
                                                    text="Overall, how effortless would you rate your experience during the last session?", height=text_height)
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
        stimulus.pos += (0, -600)

    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, -599])
    vertices.append([feedback_area_width / 2, -599])
    vertices.append([feedback_area_width / 2, -601])
    vertices.append([ -feedback_area_width / 2, -601])


    line = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0)

    question_number_stim = visual.TextStim(win, pos=[0, 1000], text="Question Set 1:", height= 2 * text_height)

    feedback_direction_question = visual.TextStim(win,
                                                  pos=[0, 800],
                                                  text="During the last exercise, when you were feeling effortlessly aware, did the graph tend to be above or below the green line?", height=text_height)
    feedback_direction_scale = visual.RatingScale(win,
                                                  pos=[0, 600],
                                                  choices=['Above', 'Below'])

    feedback_direction_confidence_question = visual.TextStim(win,
                               pos=[0, 150],
                               text="How confident are you in your answer to the above question?", height=text_height)
    feedback_direction_confidence_scale = visual.RatingScale(win,
                                                  low=0,
                                                  high=10,
                                                  labels=["Not at all", "Perfectly"],
                                                  scale=None,
                                                  pos=[0, 20])

    while feedback_direction_scale.noResponse or feedback_direction_confidence_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        feedback_direction_confidence_question.draw()
        feedback_direction_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        line.draw()
        question_number_stim.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())
    answers.append(feedback_direction_confidence_scale.getRating())

    feedback_baseline_question = visual.TextStim(win,
                            pos=[0, 800],
                            text="During the last exercise, when you were not feeling effortlessly aware, did the graph tend to be above or below the green line?", height=text_height)
    feedback_baseline_scale = visual.RatingScale(win,
                                     pos=[0, 600],
                                     choices=['Above', 'Below'])

    feedback_baseline_confidence_question = visual.TextStim(win,
                                                            pos=[0, 150],
                                                            text="How confident are you in your answer to the above question?",
                                                            height=text_height)
    feedback_baseline_confidence_scale = visual.RatingScale(win,
                                                            low=0,
                                                            high=10,
                                                            labels=["Not at all", "Perfectly"],
                                                            scale=None,
                                                            pos=[0, 20])
    question_number_stim.setText("Question Set 2:")

    while feedback_baseline_scale.noResponse or feedback_baseline_confidence_scale.noResponse:
        feedback_baseline_question.draw()
        feedback_baseline_scale.draw()
        feedback_baseline_confidence_question.draw()
        feedback_baseline_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        line.draw()
        question_number_stim.draw()
        win.flip()
    answers.append(feedback_baseline_scale.getRating())
    answers.append(feedback_baseline_confidence_scale.getRating())

    feedback_baseline_question = visual.TextStim(win,
                                                 pos=[0, 800],
                                                 text="During the last exercise, when you were feeling more effortlessly aware, was the graph overall higher or lower?",
                                                 height=text_height)
    feedback_baseline_scale = visual.RatingScale(win,
                                                 pos=[0, 600],
                                                 choices=['Higher', 'Lower'])

    feedback_baseline_confidence_question = visual.TextStim(win,
                                                            pos=[0, 150],
                                                            text="How confident are you in your answer to the above question?",
                                                            height=text_height)
    feedback_baseline_confidence_scale = visual.RatingScale(win,
                                                            low=0,
                                                            high=10,
                                                            labels=["Not at all", "Perfectly"],
                                                            scale=None,
                                                            pos=[0, 20])
    question_number_stim.setText("Question Set 3:")

    while feedback_baseline_scale.noResponse or feedback_baseline_confidence_scale.noResponse:
        feedback_baseline_question.draw()
        feedback_baseline_scale.draw()
        feedback_baseline_confidence_question.draw()
        feedback_baseline_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        line.draw()
        question_number_stim.draw()
        win.flip()
    answers.append(feedback_baseline_scale.getRating())
    answers.append(feedback_baseline_confidence_scale.getRating())

    feedback_baseline_question = visual.TextStim(win,
                                                 pos=[0, 800],
                                                 text="During the last exercise, when you were feeling less effortlessly aware, was the graph overall higher or lower?",
                                                 height=text_height)
    feedback_baseline_scale = visual.RatingScale(win,
                                                 pos=[0, 600],
                                                 choices=['Higher', 'Lower'])

    feedback_baseline_confidence_question = visual.TextStim(win,
                                                            pos=[0, 150],
                                                            text="How confident are you in your answer to the above question?",
                                                            height=text_height)
    feedback_baseline_confidence_scale = visual.RatingScale(win,
                                                            low=0,
                                                            high=10,
                                                            labels=["Not at all", "Perfectly"],
                                                            scale=None,
                                                            pos=[0, 20])
    question_number_stim.setText("Question Set 4:")

    while feedback_baseline_scale.noResponse or feedback_baseline_confidence_scale.noResponse:
        feedback_baseline_question.draw()
        feedback_baseline_scale.draw()
        feedback_baseline_confidence_question.draw()
        feedback_baseline_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        line.draw()
        question_number_stim.draw()
        win.flip()
    answers.append(feedback_baseline_scale.getRating())
    answers.append(feedback_baseline_confidence_scale.getRating())

    effortless_awareness_question = visual.TextStim(win,
                                                    pos=[0, 800],
                                                    text="Overall, how effortless would you rate your experience during the last session?",
                                                    height = text_height)
    effortless_awareness_scale = visual.RatingScale(win,pos=[0, 600], low=0, high=10,labels=["Not at all effortless", "Extremely effortless"], scale=None)

    question_number_stim.setText("Question Set 5:")

    while effortless_awareness_scale.noResponse:
        effortless_awareness_question.draw()
        effortless_awareness_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        line.draw()
        question_number_stim.draw()
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
                            pos=[0, 800],
                            text="Across all sessions so far, when you were feeling more effortlessly aware was the graph above or below the green line?",
                            height=text_height)
    feedback_direction_scale = visual.RatingScale(win,pos=[0, 600],
                                     choices=['Upward', 'Downward'])
    while feedback_direction_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())

    feedback_direction_confidence_question = visual.TextStim(win,
                                                    pos=[0, 800],
                                                    text="How confident are you in your answer to the previous question?",
                                                    height=text_height)
    feedback_direction_confidence_scale = visual.RatingScale(win,pos=[0, 600], low=0, high=10,labels=["Not at all", "Perfectly"], scale=None)

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
    smoothing_window_size = 30

    neurofeedback_values = []
    # just do it sort of like the live version
    for frame in range(priming_length):
        buffer = map(lambda channel: channel[int(round(frame * (sample_rate/60))):int(round((frame + 60) * (sample_rate/60)))], feedback_signal)

        buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), buffer)
        alpha_power = np.mean(buffer_alpha_powers)
        alpha_powers.append(alpha_power)

        if frame % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
            # use gaussian smoothed alpha power to determine neurofeedback value
            neurofeedback_values.append(neurofeedback_value(alpha_powers, baseline) * 10)

    return neurofeedback_values

def feedback_values_from_eeg(subject_id, set, run):
    baseline_path = "experiment_data/subject_{0}/set_{1}/run_{2}/baseline/eeg.edf".format(subject_id - 1, set, run, type)
    f = pyedflib.EdfReader(baseline_path)
    n = f.signals_in_file
    signal_labels = f.getSignalLabels()
    baseline_eeg = np.zeros((n, f.getNSamples()[0]))
    for i in np.arange(n):
        baseline_eeg[i, :] = f.readSignal(i)

    ipaf = np.mean(map(lambda samples: individual_peak_alpha(samples), [baseline_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, ipaf), [baseline_eeg[i] for i in baseline_channels]))

    trial_path = "experiment_data/subject_{0}/set_{1}/run_{2}/trial/eeg.edf".format(subject_id - 1, set, run, type)
    f = pyedflib.EdfReader(trial_path)
    n = f.signals_in_file
    signal_labels = f.getSignalLabels()
    trial_sham_eeg = np.zeros((n, f.getNSamples()[0]))
    for i in np.arange(n):
        trial_sham_eeg[i, :] = f.readSignal(i)

    feedback_values = []
    alpha_powers = []
    feedback_length = (len(trial_sham_eeg[i]) / 125) * 60
    # just do it sort of like the live versions

    for frame in range(feedback_length):
        buffer = map(lambda channel: channel[int(frame * round(sample_rate/60)):int((frame + 60) * round(sample_rate/60))], [trial_sham_eeg[i] for i in neurofeedback_channels])

        buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), buffer)
        alpha_power = np.mean(buffer_alpha_powers)
        alpha_powers.append(alpha_power)
        if frame % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
            feedback_values.append(neurofeedback_value(alpha_powers, baseline_frontal_alpha_power))
    return feedback_values

def stimuli_from_neurofeedback_values(win, values, neurofeedback_length, bar):
    neurofeedback_stimuli = []
    total_bars = ((neurofeedback_length) / frames_per_bar)
    feedback_area_width = (window_x - window_x / 10)
    bar_width = feedback_area_width / total_bars
    last_neurofeedback_value = None

    vertices = []
    vertices.append([0 - feedback_area_width / 2, 0]) #the initial vertex

    for index, value in enumerate(values[-(total_bars):]):
        if last_neurofeedback_value is not None and value * last_neurofeedback_value < 0:  # it crossed over 0
            a = [(index - 1) * bar_width - feedback_area_width / 2, last_neurofeedback_value]
            b = [index * bar_width - feedback_area_width / 2, value]
            slope = (b[1] - a[1]) / (b[0] - a[0])
            x_int = a[0] - a[1] / slope
            vertices.append([x_int, 0]) #the point where the line from the last value to the new value hits 0 to close the last polygon
            neurofeedback_stimulus = visual.ShapeStim(
                win=win,
                vertices=vertices,
                closeShape=True,
                fillColor="white")
            neurofeedback_stimuli.append(neurofeedback_stimulus)
            vertices = []
            vertices.append([x_int, 0]) #the point where the line from the last value to the new value hits 0 to start the new polygon
            vertices.append(b) #the point for the new feedback stimulus
        else:
            vertices.append([index * bar_width - feedback_area_width / 2, value]) #the point for the new feedback stimulus
        last_neurofeedback_value = value

    vertices.append([bar * bar_width - feedback_area_width / 2, 0]) #the end vertex
    neurofeedback_stimulus = visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="white")
    neurofeedback_stimuli.append(neurofeedback_stimulus)
    for stimulus in neurofeedback_stimuli:  # shift and scale all existing stimuli
        stimulus.pos += (bar_width / 2, 0)

    return neurofeedback_stimuli

def baseline_line_stimulus(win):
    feedback_area_width = (window_x - window_x / 10)

    vertices = []
    vertices.append([ -feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, 1])
    vertices.append([feedback_area_width / 2, -1])
    vertices.append([ -feedback_area_width / 2, -1])

    return visual.ShapeStim(
        win=win,
        vertices=vertices,
        closeShape=True,
        fillColor="greenyellow",
        lineWidth=0)

# returns the percentage that the current power is above the baseline power, smoothed by a gaussian
def neurofeedback_value(power_values, baseline):
    smoothing_window_size = 30
    smoothed_alpha_powers = filters.gaussian_filter1d(power_values[len(power_values) - smoothing_window_size:], 1)
    feedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers) / 2] / baseline) - 1) * 100
    if feedback_value > 250: # Cap feedback value at 250% of baseline, since those are certainly artifacts
        feedback_value = 250.0
    return feedback_value

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

def save_participant_details(data, subject_id):
    path = "experiment_data/subject_{0}".format(subject_id)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    import csv

    with open('experiment_data/subject_{0}/participant_info.csv'.format(subject_id), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Age", "Handedness", "Gender", 'Sex', "dateStr", 'group'])  # header row
        writer.writerow(
            [data['age'], data['handedness'], data['gender'], data['sex'], data['dateStr'], data['group']])

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

def further_instructions(win, section):
    message1 = visual.TextStim(win, pos=[0, +40], text='Please ask the research assistant for further instructions',
                               height=text_height)
    message2 = visual.TextStim(win, pos=[0, -40], text="Press a key when ready.", height=text_height)
    message3 = visual.TextStim(win, pos=[1400, 1000], text=section,
                               height=text_height)

    message1.draw()
    message2.draw()
    message3.draw()
    win.flip()
    event.waitKeys()

def thank_you_message(win):
    message1 = visual.TextStim(win, pos=[0, +40], text='Thank you for completing the experiment',
                               height=text_height)
    message2 = visual.TextStim(win, pos=[0, -40], text="Press a key to exit", height=text_height)
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()


class EEGEvent:
    latency = 0.0
    type = ""
    value = ""

    def __init__(self, type, latency, value):
        self.type = type
        self.latency = latency
        self.value = value

main()