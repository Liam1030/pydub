import itertools
import numpy as np

from .utils import db_to_float


def detect_silence(audio_segment, min_silence_len=500, max_silence_len=5000, silence_thresh=-16, seek_step=100):
    seg_len = len(audio_segment)

    # you can't have a silent portion of a sound that is longer than the sound
    if seg_len < min_silence_len:
        return []

    # convert silence threshold to a float value (so we can compare it to rms)
    silence_thresh = db_to_float(silence_thresh) * audio_segment.max_possible_amplitude * 2

    # find silence and add start and end indicies to the to_cut list
    silence_starts = []

    # check successive (1 sec by default) chunk of sound for silence
    # try a chunk at every "seek step" (or every chunk for a seek step == 1)
    last_slice_start = seg_len - min_silence_len
    slice_starts = range(0, last_slice_start + seek_step, seek_step)

    # guarantee last_slice_start is included in the range
    # to make sure the last portion of the audio is seached
    if last_slice_start % seek_step:
        slice_starts = itertools.chain(slice_starts, [last_slice_start])

    for i in slice_starts:
        audio_slice = audio_segment[i:i + seek_step]
        if audio_slice.rms <= silence_thresh:
            silence_starts.append(i)

    # short circuit when there is no silence
    if not silence_starts:
        return []

    # combine the silence we detected into ranges (start ms - end ms)
    silent_ranges = []

    prev_i = silence_starts.pop(0)
    current_range_start = prev_i
    current_range_end = prev_i + seek_step

    for silence_start_i in silence_starts:
        # if not continuous, it will be regarded as a separate split
        if silence_start_i != current_range_end:
             silence_duration = current_range_end - current_range_start

             if silence_duration > max_silence_len:
                 raise Exception("""Some silence slices duration exceed maximum value,
                 please reduce the silence threshold!""")

             if silence_duration >= min_silence_len:
                 silent_ranges.append([current_range_start, current_range_end])
             current_range_start = silence_start_i

        prev_i = silence_start_i
        current_range_end = prev_i + seek_step

    if current_range_end - current_range_start >= min_silence_len:
        silent_ranges.append([current_range_start, current_range_end])

    return silent_ranges


def detect_nonsilence(audio_segment, min_silence_len=500, max_silence_len=5000,
                     silence_thresh=-16, keep_silence=100, seek_step=100,
                     min_nonsilence_len=5000, max_nonsilence_len=15000):
    silent_ranges = detect_silence(audio_segment, min_silence_len, max_silence_len,
                                   silence_thresh, seek_step)
    len_seg = len(audio_segment)

    # if there is no silence, the whole thing is nonsilence
    if not silent_ranges:
        return [[0, len_seg]]

    # short circuit when the whole audio segment is silent
    if silent_ranges[0][0] == 0 and silent_ranges[0][1] == len_seg:
        return []

    prev_i = 0
    nonsilence_ranges = []

    for i in range(0, len(silent_ranges)):
        start_i = silent_ranges[i][0]
        end_i = silent_ranges[i][1]
        curr_i = start_i + keep_silence

        nonsilence_duration = curr_i - prev_i
        if nonsilence_duration <= max_nonsilence_len:
            if i > 0 and last_duration + nonsilence_duration <= (max_nonsilence_len + min_nonsilence_len) // 2:
                # merge with previous range which is less than min_nonsilence_len
                nonsilence_ranges[-1][1] = curr_i;
                last_duration = curr_i - nonsilence_ranges[-1][0]
            else:
                nonsilence_ranges.append([prev_i, curr_i])
                last_duration = curr_i - prev_i
        else:
            raise Exception("""Some voice slices out of range, you can insert
            some silence slices by:
            1. increase the silence threshold; and
            2. shrink the minimum silence slice.""")
        prev_i = curr_i 

    if end_i != len_seg and len_seg - prev_i >= min_nonsilence_len:
        nonsilence_ranges.append([prev_i, len_seg])

    if nonsilence_ranges[-1][1] - nonsilence_ranges[-1][0] < min_nonsilence_len:
        nonsilence_ranges.pop()

    if nonsilence_ranges[0] == [0, 0]:
        nonsilence_ranges.pop(0)

    return nonsilence_ranges


def split_on_silence(audio_segment, min_silence_len=500, max_silence_len=5000,
                     silence_thresh=-16, keep_silence=100, seek_step=100,
                     min_nonsilence_len=5000, max_nonsilence_len=15000):
    """
    audio_segment - original pydub.AudioSegment() object

    min_silence_len - (in ms) minimum length of a silence to be used for
        a split. default: 1000ms

    silence_thresh - (in dBFS) anything quieter than this will be
        considered silence. default: -16dBFS

    keep_silence - (in ms) amount of silence to leave at the beginning
        and end of the chunks. Keeps the sound from sounding like it is
        abruptly cut off. (default: 100ms)

    seek_step - the span between two adjacent seek points as well as basic
        unit of chunks in silence detect

    min_nonsilence_len - (in ms) minimum length of a nonsilence to be used
        for a split. default: 5000ms

    max_nonsilence_len - (in ms) maximum length of a nonsilence to be used
        for a split. default: 15000ms
    """

    not_silence_ranges = detect_nonsilence(audio_segment, min_silence_len, max_silence_len,
                                           silence_thresh, keep_silence, seek_step,
                                           min_nonsilence_len, max_nonsilence_len)

    chunks = []
    for start_i, end_i in not_silence_ranges:
        start_i = max(0, start_i - keep_silence)
        end_i += keep_silence
        end_i = len(audio_segment) if end_i > len(audio_segment) else end_i

        chunks.append(audio_segment[start_i:end_i])

    return chunks
