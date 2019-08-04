ROS VAD
=================

## Overview

This is a ROS package for detecting voice activity. It acts as a wrapper around [webrtcvad](https://github.com/wiseman/py-webrtcvad) and implements more naive detection algorithms using volume and energy.

## Nodes

### VAD

Detects vocal activity.

Example usage:

```bash
rosrun ros_vad vad.py _input_topic:=/mic/data __name:=vad
```

#### Published Topics

**~complete** ([audio_io_msgs/AudioData](https://github.com/sean-hackett/audio_io/blob/master/audio_io_msgs/msg/AudioData.msg)): A complete utterance that was terminated by a frame not in a segment of vocal activity. Made available at the completion of an utterance.

**~chunks** ([audio_io_msgs/AudioData](https://github.com/sean-hackett/audio_io/blob/master/audio_io_msgs/msg/AudioData.msg)): Chunks from utterances. Made available while an utterance is underway.

#### Parameters

**~input_topic** (string): A ROS topic publishing `AudioData` messages.

**~algorithm** (string, default: 'webrtcvad'): Algorithm for determining if a frame is speech or non-speech. Must be 'webrtcvad', 'volume', or 'energy'.

**~frame_duration** (float, default: 30): Duration (ms) of analysis frames.

**~neighborhood_duration** (float, default: 300): Duration (ms) of (sliding) analysis neighborhood. Should be multiple of frame_duration. Must be 10, 20, or 30 for webrtcvad.

**~aggressiveness** (int, default: 1): [Only for webrtcvad] How aggressive webrtcvad should be in filtering out non-speech. Must be in [0., 3.].

**~threshold** (int, default: 0.5): [Only for volume, energy] Minimum average volume or energy that a frame must have to be considered speech.

**~ratio** (int, default: 0.9): The minimum proportion of frames in a neighborhood required for the neighborhood to be considered a segment of vocal activity.

**~calibrate** (bool, default: False): Log the value computed for each frame by `algorithm`, prior to thresholding. For volume, this would be the volume for the frame.

**~verbose** (bool, default: False): Log True if a frame is in a segment of vocal activity, False if not.

## Approach

The script divides an audio stream into frames of duration `frame_duration`. Each frame is analyzed with the specified algorithm to determine if it is a speech or non-speech frame.

Frames are typically short in duration, the default being 30ms. A single 30ms speech frame surrounded by non-speech frames would not likely considered vocal activity. Therefore, the script analyzes the neighboring frames around each frame to determine if a frame is in a neighborhood that constitutes vocal activity.

A neighborhood constitutes vocal activity if the proportion of speech frames in the neighborhood exceeds `ratio`. Neighborhoods are founding by sliding time windows of duration `neighborhood_duration` along with steps of `frame_duration`. Each neighborhood therefore contains `neighborhood_duration`/`window_duration` frames.

`~chunks` receive all frames that are in neighborhoods with vocal activity. If consecutive frames are in neighborhoods with vocal activity, the frames are stored in a buffer. When a frame not in a neighborhood with vocal activity, the buffer is dumped to `~complete`.

## Algorithms

### WebRTC VAD
A frame is considered speech is the WebRTC VAD API says it so. See [here](https://github.com/wiseman/py-webrtcvad) for more info.

### Volume
A frame is considered speech if its average volume (normalized to [0,1]) is greater than `threshold`.

### Energy
A frame is considered speech if its average energy is greater than `threshold`. Energy is found by normalizing the frame of [0,1] and compute the its mean-square.
