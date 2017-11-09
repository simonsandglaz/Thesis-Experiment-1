from __future__ import print_function

from psychopy import visual
from psychopy import core, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import time, numpy as np, random
import pyedflib
import os
import errno

from pylsl import StreamInlet, resolve_stream
from pylsl import StreamInfo, StreamOutlet

sample_rate = 125 # 125Hz in 16 channel mode for openBCI
window_x = 1280
window_y = 720

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
    inlet, outlet = connect_to_EEG()

    #read stimuli adjectives for baseline task
    priming_stimuli = read_priming_stimuli()

    #set up experiment window
    win = visual.Window([window_x,window_y], allowGUI=True, monitor='testMonitor', units='pix')

    stimuli_index = 0
    # # 1. Meditation without feedback (2 runs, 4 minutes each)
    # for i in range(2):
    #     baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
    #     save_edf(eeg, events, subject_id, 0, i, 'baseline')
    #     eeg, events = show_no_feedback(win, inlet, outlet, baseline, ipaf)
    #     save_edf(eeg, events, subject_id, 0, i, 'trial')
    #     stimuli_index += 1
    #
    # # 2. Meditation with offline feedback (feedback graph shown offline after each run; 4 runs, 1.5 minutes each)
    # for i in range(4):
    #     baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
    #     save_edf(eeg, events, subject_id, 1, i, 'baseline')
    #     eeg, events, feedback_stimuli, feedback_values = show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf)
    #     save_edf(eeg, events, subject_id, 1, i, 'trial')
    #     show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 1, i)
    #     if i == 4:
    #         show_final_feedback_questions(win, 1, i)
    #     stimuli_index += 1

    # 3. Meditation with real-time feedback (4 runs, 1.5 minutes each)
    # for i in range(3):
    #     baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
    #     save_edf(eeg, events, subject_id, 2, i, 'baseline')
    #     eeg, events, feedback_stimuli, feedback_values = show_neurofeedback(win, inlet, outlet, baseline, ipaf)
    #     save_edf(eeg, events, subject_id, 2, i, 'trial')
    #     show_run_feedback_questions(win, feedback_stimuli, feedback_values, subject_id, 2, i)
    #     if i == 4:
    #         show_final_feedback_questions(win, subject_id, 2, i)
    #     stimuli_index += 1

    # 4. "Free-play" session. Participants are allowed to experiment with the feedback, using strategies of their own choosing. (2 runs, 7 minutes each).
    for i in range(2):
        baseline, ipaf, eeg, events = show_baseline(win, inlet, outlet, priming_stimuli[stimuli_index][0])
        save_edf(eeg, events, subject_id, 3, i, 'baseline')
        eeg, events = show_neurofeedback_free_play(win, inlet, outlet, baseline, ipaf)
        save_edf(eeg, events, subject_id, 3, i, 'trial')
        stimuli_index += 1


    win.close()
    core.quit()

def show_baseline(win, inlet, outlet, priming_stimulus):
    # send a marker to LSL for start of baseline
    message1 = visual.TextStim(win, pos=[0,+20],text='Consider how the following word describes you')
    message2 = visual.TextStim(win, pos=[0,-20],text="Press a key when ready.")
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

    # show some priming stimuli while recording baseline data
    priming_length = 1800 # 30 seconds
    # priming_length = 120
    fixation_length = 60 # 1 second

    trialClock = core.Clock()
    events.append(EEGEvent("fixation", 0, fixation_length/60))
    for frameN in range(priming_length):
        chunk, timestamps = inlet.pull_chunk()

        for sample in chunk: #put new samples in the eeg buffer
            # print(max(sample))
            if max(sample) < 80:
                for index, channel_data in enumerate(sample):
                    full_eeg_no_artifacts[index].append(channel_data)
            else:
                print("eye blink")
            for index, channel_data in enumerate(sample):
                full_eeg[index].append(channel_data)

        if 0 <= frameN < fixation_length:  # present fixation for a subset of frames
            fixation.draw()
        if frameN == fixation_length + 1:
            events.append(EEGEvent("priming_stimulus", trialClock.getTime(), priming_stimulus))
        if fixation_length <= frameN < priming_length + fixation_length:  # present stim for a different subset
            visual.TextStim(win, pos=[0, 0], text=priming_stimulus).draw()  # trait-adjective


        win.flip()

    peak_alpha = np.mean(map(lambda samples: individual_peak_alpha(samples), [full_eeg[i] for i in peak_alpha_channels]))

    baseline_frontal_alpha_power = np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg[i] for i in baseline_channels]))
    max_baseline_frontal_alpha_signal = np.max(map(lambda channel: max(channel), [full_eeg[i] for i in baseline_channels]))
    max_baseline_frontal_alpha_signal_no_artifacts = np.max(map(lambda channel: max(channel), [full_eeg_no_artifacts[i] for i in baseline_channels]))
    baseline_frontal_alpha_power_no_artifacts = np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg_no_artifacts[i] for i in baseline_channels]))
    # print(max_baseline_frontal_alpha_signal)
    # print(baseline_frontal_alpha_power)
    # print(max_baseline_frontal_alpha_signal_no_artifacts)
    # print(np.mean(map(lambda samples: eeg_power(samples, peak_alpha), [full_eeg_no_artifacts[i] for i in baseline_channels])))

    # return baseline_frontal_alpha_power_no_artifacts, peak_alpha, full_eeg, events
    return baseline_frontal_alpha_power, peak_alpha, full_eeg, events

def show_no_feedback(win, inlet, outlet, priming_stimulus, ipaf):

    message1 = visual.TextStim(win, pos=[0, +20], text='Perform the meditation practice while keeping your eyes focused on the dot in the center of the screen')
    message2 = visual.TextStim(win, pos=[0, -20], text="Press a key when ready.")
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)



    full_eeg = [[] for i in range(len(channels))]
    events = []

    # show some priming stimuli while recording baseline data
    meditation_length = 300
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

    message1 = visual.TextStim(win, pos=[0,+20],text='Please perform the instructed meditation practice')
    message2 = visual.TextStim(win, pos=[0,-20],text="Press a key when ready.")
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()


    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 30
    smoothing_window_size = 30
    neurofeedback_length = 5400 # 1.5 minutes
    # neurofeedback_length = 600
    fixation_length = 120
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
            alpha_powers.append(alpha_power)

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                smoothed_alpha_powers = filters.gaussian_filter1d(alpha_powers[len(alpha_powers) - smoothing_window_size:], 1)
                neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers)/2] / baseline) - 1) * 100
                # neurofeedback_value = smoothed_alpha_powers[len(smoothed_alpha_powers)/2] - baseline

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

        win.flip()

    return full_eeg, events, neurofeedback_stimuli, neurofeedback_values

def show_offline_neurofeedback(win, inlet, outlet, baseline, ipaf):
    import scipy.ndimage.filters as filters
    neurofeedback_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]

    message1 = visual.TextStim(win, pos=[0,+20],text='Please perform the instructed meditation practice')
    message2 = visual.TextStim(win, pos=[0,-20],text="Press a key when ready.")
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []
    neurofeedback_stimuli = []
    neurofeedback_values = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 30
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

        if 0 <= frameN < 120:  # present fixation while initial eeg data collected, so FFT makes sense
            fixation.draw()
        if 120 <= frameN < neurofeedback_length:
            buffer_alpha_powers = map(lambda channel: eeg_power(channel, ipaf), neurofeedback_eeg_buffer)
            alpha_power = np.mean(buffer_alpha_powers)
            alpha_powers.append(alpha_power)

            if frameN % frames_per_bar == 0:  # make a new stimulus bar every frames_per_bar frames
                # use gaussian smoothed alpha power to determine neurofeedback value
                smoothed_alpha_powers = filters.gaussian_filter1d(
                    alpha_powers[len(alpha_powers) - smoothing_window_size:], 1)
                neurofeedback_value = ((smoothed_alpha_powers[len(smoothed_alpha_powers)/2] / baseline) - 1) * 100
                # neurofeedback_value = smoothed_alpha_powers[len(smoothed_alpha_powers) / 2] - baseline

                bar = ((frameN - 120) / frames_per_bar)  # the nth bar of the feedback
                total_bars = ((neurofeedback_length - 120) / frames_per_bar)
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
    import scipy.ndimage.filters as filters
    neurofeedback_channels = [channels["Fp1"],
                              channels["Fp2"],
                              channels["Fpz"],
                              channels["AF3"],
                              channels["AF4"],
                              channels["Fz"]]

    message1 = visual.TextStim(win, pos=[0, +20], text='Experiment with methods to manipulate the graph')
    message2 = visual.TextStim(win, pos=[0, -20], text="Press a key when ready.")
    message1.draw()
    message2.draw()
    win.flip()
    event.waitKeys()

    neurofeedback_eeg_buffer = [[] for i in range(len(neurofeedback_channels))]
    full_eeg = [[] for i in range(len(channels))]
    events = []

    neurofeedback_stimuli = []
    alpha_powers = []

    fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                                  tex=None, mask='circle', size=20)

    frames_per_bar = 30
    smoothing_window_size = 30
    neurofeedback_length = 25200  # 7 minutes
    visible_neurofeedback_length = 1200
    fixation_length = 120
    events.append(EEGEvent("fixation", 0, fixation_length / 60))

    trialClock = core.Clock()

    for frameN in range(neurofeedback_length):
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

        win.flip()

    return full_eeg, events

def show_run_feedback_questions(win, neurofeedback_stimuli, neurofeedback_values, subject_id, set, run):

    answers = []

    neurofeedback_max = max(neurofeedback_values)
    neurofeedback_min = min(neurofeedback_values)
    scaling = 100/max(max(neurofeedback_max, 0), abs(min(neurofeedback_min, 0)))
    for stimulus in neurofeedback_stimuli: # shift and scale all existing stimuli to the down to make room for questions
        stimulus.size *= (1, scaling)
        stimulus.pos += (0, -150)

    feedback_direction_question = visual.TextStim(win,
                                                  pos=[0, 250],
                                                  text="Do increases or decreases in the graph correspond to increases in your experience of effortless awareness?")
    feedback_direction_scale = visual.RatingScale(win,
                                                  pos=[0, 120],
                                                  choices=['Increases', 'Decreases'])

    while feedback_direction_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())

    feedback_direction_confidence_question = visual.TextStim(win,
                               pos=[0, 250],
                               text="How confident are you that effortless awareness corresponds with {} in the graph?".format(feedback_direction_scale.getRating().lower()))
    feedback_direction_confidence_scale = visual.RatingScale(win,
                                                  low=0,
                                                  high=10,
                                                  labels=["Not at all", "Perfectly"],
                                                  scale=None,
                                                  pos=[0, 120])

    while feedback_direction_confidence_scale.noResponse:
        feedback_direction_confidence_question.draw()
        feedback_direction_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        win.flip()
    answers.append(feedback_direction_confidence_scale.getRating())


    feedback_baseline_question = visual.TextStim(win,
                               pos=[0, 250],
                               text="Does your experience of effortless awareness correspond with the graph being upward or downward?")
    feedback_baseline_scale = visual.RatingScale(win,
                                     pos=[0, 120],
                                     choices=['Upward', 'Downward'])

    while feedback_baseline_scale.noResponse:
        feedback_baseline_question.draw()
        feedback_baseline_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        win.flip()
    answers.append(feedback_baseline_scale.getRating())

    feedback_baseline_confidence_question = visual.TextStim(win,
                                                 pos=[0, 250],
                                                 text="How confident are you that effortless awareness corresponds with the graph being {}?".format(feedback_baseline_scale.getRating().lower()))
    feedback_baseline_confidence_scale = visual.RatingScale(win,
                                                  low=0,
                                                  high=10,
                                                  labels=["Not at all", "Perfectly"],
                                                  scale=None,
                                                  pos=[0, 120])

    while feedback_baseline_confidence_scale.noResponse:
        feedback_baseline_confidence_question.draw()
        feedback_baseline_confidence_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        win.flip()
    answers.append(feedback_baseline_confidence_scale.getRating())

    effortless_awareness_question = visual.TextStim(win,
                                                    pos=[0, 250],
                                                    text="How effortless was your awareness overall during the previous meditation session?")
    effortless_awareness_scale = visual.RatingScale(win,pos=[0, 120], low=0, high=10,labels=["Not at all effortless", "Extremely effortless"], scale=None)

    while effortless_awareness_scale.noResponse:
        effortless_awareness_question.draw()
        effortless_awareness_scale.draw()
        for stimulus in neurofeedback_stimuli:
            stimulus.draw()
        win.flip()
    answers.append(effortless_awareness_scale.getRating())

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
                               text="Across all experiments so far, do you think effortless awareness corresponds with the graph being upward or downward?")
    feedback_direction_scale = visual.RatingScale(win,
                                     choices=['Upward', 'Downward'])
    while feedback_direction_scale.noResponse:
        feedback_direction_question.draw()
        feedback_direction_scale.draw()
        win.flip()
    answers.append(feedback_direction_scale.getRating())

    feedback_direction_confidence_question = visual.TextStim(win,
                                                    pos=[0, 250],
                                                    text="How well does the graph correspond with your experience during effortless awareness and its opposite?")
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
    ps = np.abs(np.fft.fft(samples)) ** 2  # power spectrum

    time_step = 1.0 / sample_rate
    freqs = np.fft.fftfreq(len(samples), time_step)
    idx = np.argsort(freqs)

    alpha_bins = 0
    total_alpha_power = 0

    theta_bins = 0
    total_theta_power = 0

    for freq, power in zip(freqs[idx], ps[idx]):
        if freq >= ipaf - 2.5 and freq <= ipaf + 2.5:
            alpha_bins += 1
            total_alpha_power += power
        elif freq >= 3 and freq <= ipaf - 3:
            theta_bins += 1
            total_theta_power += power

    return (total_alpha_power / alpha_bins)/len(samples)
    # return (total_theta_power / theta_bins)/len(samples)

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