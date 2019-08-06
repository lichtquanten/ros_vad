#!/usr/bin/env python
from audio_io.utils import width_to_dtype
import numpy as np
import rospy
from rospywrapper import TopicSource
import webrtcvad

from audio_io_msgs.msg import AudioData
from std_msgs.msg import Header

from ros_vad.grouper import BlockArrLike, Neighborhood

ALGORITHMS=("webrtcvad", "volume", "energy")

def main():
    # Get parameters
    input_topic = rospy.get_param('~input_topic')
    aggressiveness = rospy.get_param('~aggressiveness', None)
    frame_duration = rospy.get_param('~frame_duration', 30)
    neighborhood_duration = rospy.get_param('~window_duration', 300)
    algorithm = rospy.get_param('~algorithm', "webrtcvad")
    threshold = rospy.get_param('~threshold', 0.5)
    ratio = rospy.get_param('~ratio', 0.9)
    calibrate = rospy.get_param('~calibrate', False)
    verbose = rospy.get_param('~verbose', False)

    pub_complete = rospy.Publisher('~complete', AudioData, queue_size=10)
    pub_chunks = rospy.Publisher('~chunks', AudioData, queue_size=10)

    # Validate parameters
    if algorithm not in ALGORITHMS:
        raise Exception("Algorithm must be one of {}.".format(ALGORITHMS))

    if algorithm == 'webrtcvad':
        if frame_duration not in (10, 20, 30):
            raise Exception("""Frame duration (ms) must be 10, 20, or 30 for
            webrtcvad""")
        if aggressiveness is not None:
            if not 0 <= aggressiveness <= 3:
                raise Exception("Aggressiveness must be between 0.0 and 3.0.")
            vad = webrtcvad.Vad(aggressiveness)
        else:
            vad = webrtcvad.Vad()

    source = TopicSource(input_topic, AudioData)
    with source:
        # Initialize a buffer for complete utterances
        complete_buffer = np.array([], np.uint8)
        complete_buffer_t = None

        initialized = False

        # Iterate over messages
        for msg, t in source:
            if not initialized:
                initialized = True
                # Validate audio configuration
                if not msg.sample_rate in (8000, 16000, 32000, 48000):
                    raise Exception("""Sample rate must be 8000, 16000, 32000,
                    or 48000. Sample rate provided is {}.""".format(msg.sample_rate))
                if msg.sample_width != 2:
                    raise Exception("""Sample width must be 2. Sample width
                    provided is {}.""".format(msg.sample_width))
                if msg.num_channels != 1:
                    raise Exception("Only single channel audio supported.")

                # Find numpy data type
                dtype = width_to_dtype(msg.sample_width)

                # Factor of 2 for sample width of 2
                # Initialize frame buffer
                frame_length = int(msg.sample_rate * (frame_duration / 1000.)) * 2
                frames = BlockArrLike(frame_length, np.array([], np.uint8), np.append)

                def is_valid(nbhd):
                    valids = [valid for frame, valid in nbhd]
                    return (sum(valids) / float(len(valids))) >= ratio

                nbhd_length = int(neighborhood_duration / frame_duration)
                nbhds = Neighborhood(is_valid, nbhd_length)

            duration = rospy.Duration(
                float(len(msg.data)) / msg.num_channels / msg.sample_width / msg.sample_rate
            )

            # Add message's data to frames buffer
            frames.put(np.array(bytearray(msg.data)), msg.header.stamp, msg.header.stamp + duration)

            # Analyze frames and add to neighborhood
            for frame, start, end in frames:
                fr = str(bytearray(frame))
                if algorithm == "webrtcvad":
                    valid = vad.is_speech(fr, msg.sample_rate)
                    if calibrate:
                        rospy.loginfo('Frame is speech?: {}'.format(valid))
                else:
                    # Convert to array of samples
                    fr = np.frombuffer(fr, dtype)
                    if algorithm == "volume":
                        mean = np.mean(np.abs(fr))
                        # Normalize mean [0., 1.]
                        mean = mean / np.iinfo(dtype).max
                        if calibrate:
                            rospy.loginfo('Mean: {}'.format(mean))
                        valid = mean >= threshold
                    elif algorithm == "energy":
                        # Convert to float [0, 1]
                        fr = (fr / (np.iinfo(dtype).max * 2.)) + 0.5
                        energy = np.mean(np.square(fr))
                        if calibrate:
                            rospy.loginfo('Energy: {}'.format(energy))
                        valid = energy >= threshold
                nbhds.put((frame, valid), start, end)

            chunk_buffer = np.array([], np.uint8)
            chunk_buffer_t = None
            for (frame, _), is_in_speech, t, _ in nbhds:
                if verbose and is_in_speech:
                    rospy.loginfo('Frame is in utterance.')
                if not is_in_speech:
                    if chunk_buffer.size > 0:
                        # Flatten the bytearrays
                        data = str(bytearray(chunk_buffer))
                        print data
                        # Construct a message
                        msg.header = Header()
                        msg.header.stamp = chunk_buffer_t
                        msg.data = data
                        pub_chunks.publish(msg)
                        chunk_buffer = np.array([], np.uint8)
                        chunk_buffer_t = None
                    if complete_buffer.size > 0:
                        # Flatten the bytearrays
                        data = str(bytearray(complete_buffer))
                        # Construct a message
                        msg.header = Header()
                        msg.header.stamp = complete_buffer_t
                        msg.data = data
                        pub_complete.publish(msg)
                        complete_buffer = np.array([], np.uint8)
                        complete_buffer_t = None
                else:
                    chunk_buffer = np.append(chunk_buffer, frame)
                    if not chunk_buffer_t:
                        chunk_buffer_t = t
                    complete_buffer = np.append(complete_buffer, frame)
                    if not complete_buffer_t:
                        complete_buffer_t = t

            if chunk_buffer.size > 0:
                # Flatten the bytearrays
                data = str(bytearray(chunk_buffer))
                # Construct a message
                msg.header = Header()
                msg.header.stamp = chunk_buffer_t
                msg.data = data
                pub_chunks.publish(msg)
                chunk_buffer = []
                chunk_buffer_t = None
        if complete_buffer.size > 0:
            # Flatten the bytearrays
            data = str(bytearray(complete_buffer))
            # Construct a message
            msg.header = Header()
            msg.header.stamp = complete_buffer_t
            msg.data = data
            pub_complete.publish(msg)
            complete_buffer = []
            complete_buffer_t = None

if __name__ == '__main__':
    rospy.init_node('vad', anonymous=True)
    main()
