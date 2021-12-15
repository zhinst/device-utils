"""
Zurich Instruments LabOne Python API Utility functions for SHFQA.
"""

import time
import numpy as np

from zhinst.utils import assert_node_changes_to_expected_value


SHFQA_MAX_SIGNAL_GENERATOR_WAVEFORM_LENGTH = 4 * 2 ** 10
SHFQA_MAX_SIGNAL_GENERATOR_CARRIER_COUNT = 16
SHFQA_SAMPLING_FREQUENCY = 2e9


def max_qubits_per_channel(daq, device_id) -> int:
    """Returns the maximum number of supported qubits per channel.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

    """

    features_path = f"/{device_id}/features/"
    device_type = daq.getString(features_path + "devtype")
    options = daq.getString(features_path + "options")

    if device_type == "SHFQA4" or "16W" in options:
        return 16
    return 8


def load_sequencer_program(
    daq, device_id: str, channel_index: int, sequencer_program: str, awg_module=None
) -> None:
    """Compiles and loads a program to a specified sequencer.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying to which sequencer the program below
                           is uploaded - there is one sequencer per channel

      sequencer_program (str): sequencer program to be uploaded

      awg_module (AwgModule): awg module instance used to interact with the sequencer. If none
                              is provided, a new local instance will be created

    """

    # start by resetting the sequencer
    daq.setInt(
        f"/{device_id}/qachannels/{channel_index}/generator/reset",
        1,
    )
    daq.sync()

    timeout_compile = 10
    timeout_ready = 10

    if awg_module is None:
        awg_module = daq.awgModule()
    awg_module.set("device", device_id)
    awg_module.set("index", channel_index)
    awg_module.execute()

    t_start = time.time()
    awg_module.set("compiler/sourcestring", sequencer_program)
    timeout_occurred = False

    # start the compilation and upload
    compiler_status = awg_module.getInt("compiler/status")
    while compiler_status == -1 and not timeout_occurred:
        if time.time() - t_start > timeout_compile:
            # a timeout occurred
            timeout_occurred = True
            break
        # wait
        time.sleep(0.1)
        # query new status
        compiler_status = awg_module.getInt("compiler/status")

    # check the status after compilation and upload
    if timeout_occurred or compiler_status != 0:
        # an info, warning or error occurred - check what it is
        compiler_status = awg_module.getInt("compiler/status")
        statusstring = awg_module.getString("compiler/statusstring")
        if compiler_status == 2:
            print(
                f"Compiler info or warning for channel {channel_index}:\n"
                + statusstring
            )
        elif timeout_occurred:
            raise RuntimeError(
                f"Timeout during program compilation for channel {channel_index} after \
                    {timeout_compile} s,\n"
                + statusstring
            )
        else:
            raise RuntimeError(
                f"Failed to compile program for channel {channel_index},\n"
                + statusstring
            )

    # wait until the device becomes ready after program upload
    assert_node_changes_to_expected_value(
        daq,
        f"/{device_id}/qachannels/{channel_index}/generator/ready",
        1,
        sleep_time=0.1,
        max_repetitions=int(timeout_ready / 0.1),
    )
    time.sleep(0.1)


def configure_scope(
    daq,
    device_id: str,
    input_select: dict,
    num_samples: int,
    trigger_input: str,
    num_segments: int = 1,
    num_averages: int = 1,
    trigger_delay: int = 0,
) -> None:
    """Configures the scope for a measurement.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      input_select (dict): keys (int) map a specific scope channel with a signal source (str),
                           e.g. "channel0_signal_input". For a list of available values use
                           daq.help(f"/{device_id}/scopes/0/channels/0/inputselect")

      trigger_input (str): specifies the trigger source of the scope acquisition
                           - if set to None, the self-triggering mode of the scope becomes
                           active, which is useful e.g. for the GUI.
                           For a list of available trigger values use
                           daq.help(f"/{device_id}/scopes/0/trigger/channel")

      num_segments (int): number of distinct scope shots to be returned after ending the
                            acquisition

      num_averages (int): specifies how many times each segment should be averaged on
                            hardware; to finish a scope acquisition, the number of issued
                            triggers must be equal to num_segments * num_averages

      trigger_delay (int): delay in samples specifying the time between the start of data
                             acquisition and reception of a trigger

    """

    daq.setInt(f"/{device_id}/scopes/0/segments/count", num_segments)
    if num_segments > 1:
        daq.setInt(f"/{device_id}/scopes/0/segments/enable", 1)
    else:
        daq.setInt(f"/{device_id}/scopes/0/segments/enable", 0)

    if num_averages > 1:
        daq.setInt(f"/{device_id}/scopes/0/averaging/enable", 1)
    else:
        daq.setInt(f"/{device_id}/scopes/0/averaging/enable", 0)
    daq.setInt(
        f"/{device_id}/scopes/0/averaging/count",
        num_averages,
    )

    daq.setInt(f"/{device_id}/scopes/0/channels/*/enable", 0)
    for channel, selected_input in input_select.items():
        daq.setString(
            f"/{device_id}/scopes/0/channels/{channel}/inputselect",
            selected_input,
        )
        daq.setInt(f"/{device_id}/scopes/0/channels/{channel}/enable", 1)

        daq.setDouble(f"/{device_id}/scopes/0/trigger/delay", trigger_delay)

        if trigger_input is not None:
            daq.setString(
                f"/{device_id}/scopes/0/trigger/channel",
                trigger_input,
            )
            daq.setInt(f"/{device_id}/scopes/0/trigger/enable", 1)
        else:
            daq.setInt(f"/{device_id}/scopes/0/trigger/enable", 0)

    daq.setInt(f"/{device_id}/scopes/0/length", num_samples)


def get_scope_data(daq, device_id: str, time_out: float = 1.0) -> tuple:
    """Queries the scope for data once it has been triggered and finished the acquisition.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      time_out (optional float): maximum time to wait for the scope data in seconds

    Returns:

      Three-element tuple with:

      recorded_data (array): contains an array per scope channel with the recorded data

      recorded_data_range (array): full scale range of each scope channel

      scope_time (array): relative acquisition time for each point in recorded_data in
                          seconds starting from 0

    """

    # wait until scope has been triggered
    sleep_time = 0.005
    num_loops = int(time_out / sleep_time)
    assert_node_changes_to_expected_value(
        daq,
        f"/{device_id}/scopes/0/enable",
        0,
        sleep_time=sleep_time,
        max_repetitions=num_loops,
    )

    # read and post-process the recorded data
    recorded_data = [[], [], [], []]
    recorded_data_range = [0.0, 0.0, 0.0, 0.0]
    num_bits_of_adc = 14
    max_adc_range = 2 ** (num_bits_of_adc - 1)

    channels = range(4)
    for channel in channels:
        if daq.getInt(f"/{device_id}/scopes/0/channels/{channel}/enable"):
            path = f"/{device_id}/scopes/0/channels/{channel}/wave"
            data = daq.get(path.lower(), flat=True)
            vector = data[path]

            recorded_data[channel] = vector[0]["vector"]
            averagecount = vector[0]["properties"]["averagecount"]
            scaling = vector[0]["properties"]["scaling"]
            voltage_per_lsb = scaling * averagecount
            recorded_data_range[channel] = voltage_per_lsb * max_adc_range

    # generate the time base
    scope_time = [[], [], [], []]
    decimation_rate = 2 ** daq.getInt(f"/{device_id}/scopes/0/time")
    sampling_rate = SHFQA_SAMPLING_FREQUENCY / decimation_rate  # [Hz]
    for channel in channels:
        scope_time[channel] = (
            np.array(range(0, len(recorded_data[channel]))) / sampling_rate
        )

    return recorded_data, recorded_data_range, scope_time


def enable_sequencer(daq, device_id: str, channel_index: int, single: int) -> None:
    """Starts the sequencer of a specific channel.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which sequencer to enable - there is one
                           sequencer per channel

      single (int): 1 - disable sequencer after finishing execution
                    0 - restart sequencer after finishing execution

    """

    daq.setInt(
        f"/{device_id}/qachannels/{channel_index}/generator/single",
        single,
    )

    enable_path = f"/{device_id}/qachannels/{channel_index}/generator/enable"
    daq.setInt(enable_path, 1)
    assert_node_changes_to_expected_value(daq, enable_path, 1)


def write_to_waveform_memory(
    daq,
    device_id: str,
    channel_index: int,
    waveforms: dict,
    clear_existing: bool = True,
) -> None:
    """Writes pulses to the waveform memory of a specified generator.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which generator the waveforms below
                           are written to - there is one generator per channel

      waveforms (dict): dictionary of waveforms, the key specifies the slot to which
                        to write the value which is a complex array containing the
                        waveform samples

      clear_existing (optional bool): specify whether to clear the waveform memory
                                      before the present upload

    """
    waveforms_path = f"/{device_id}/qachannels/{channel_index}/generator/waveforms/"

    if clear_existing:
        empty_waveform = np.array([], dtype="complex128")
        for slot in range(0, max_qubits_per_channel(daq, device_id)):
            daq.setVector(
                waveforms_path + f"{slot}/wave",
                empty_waveform,
            )

    for slot, waveform in waveforms.items():
        daq.setVector(
            waveforms_path + f"{slot}/wave",
            waveform,
        )


def start_continuous_sw_trigger(
    daq, device_id: str, num_triggers: int, wait_time: float
) -> None:
    """Issues a specified number of software triggers with a certain wait time in between.
    The function guarantees reception and proper processing of all triggers by the device,
    but the time between triggers is non-deterministic by nature of software triggering.
    Only use this function for prototyping and/or cases without strong timing requirements.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      num_triggers (int): number of triggers to be issued

      wait_time (float): time between triggers in seconds

    """

    min_wait_time = 0.02
    wait_time = max(min_wait_time, wait_time)
    for _ in range(num_triggers):
        # syncSetInt() is a blocking call with non-deterministic execution time that
        # imposes a minimum time between two software triggers.
        daq.syncSetInt(f"/{device_id}/system/swtriggers/0/single", 1)
        time.sleep(wait_time)


def enable_scope(daq, device_id: str, single: int) -> None:
    """Enables the scope.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      single (int): 0 = continuous mode, 1 = single-shot
    """

    daq.setInt(f"/{device_id}/scopes/0/single", single)

    path = f"/{device_id}/scopes/0/enable"
    if daq.getInt(path) == 1:
        daq.setInt(path, 0)
        assert_node_changes_to_expected_value(daq, path, 0)
    daq.syncSetInt(path, 1)


def configure_weighted_integration(
    daq,
    device_id: str,
    channel_index: int,
    weights: dict,
    integration_delay: float = 0.0,
    clear_existing: bool = True,
) -> None:
    """Configures the weighted integration on a specified channel.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which group of integration units
                           the integration weights should be uploaded to - each
                           channel is associated with a number of integration
                           units that depend on available device options. Please
                           refer to the SHFQA manual for more details

      weights (dict): dictionary containing the complex weight vectors, where keys
                      correspond to the indices of the integration units to be configured

      integration_delay (optional float): delay in seconds before starting readout

      clear_existing (optional bool): specify whether to set all the integration weights
                                      to zero before proceeding with the present upload

    """

    assert len(weights) > 0, "'weights' cannot be empty."

    integration_path = f"/{device_id}/qachannels/{channel_index}/readout/integration/"

    if clear_existing:
        zero_weight = np.zeros(
            (SHFQA_MAX_SIGNAL_GENERATOR_WAVEFORM_LENGTH,), dtype="complex128"
        )
        for integration_unit in range(0, max_qubits_per_channel(daq, device_id)):
            daq.setVector(
                integration_path + f"weights/{integration_unit}/wave", zero_weight
            )

    for integration_unit, weight in weights.items():
        daq.setVector(integration_path + f"weights/{integration_unit}/wave", weight)

    integration_length = len(weights[0])
    daq.setInt(integration_path + "length", integration_length)
    daq.setDouble(integration_path + "delay", integration_delay)


def configure_result_logger_for_spectroscopy(
    daq,
    device_id: str,
    channel_index: int,
    result_length: int,
    num_averages: int = 1,
    averaging_mode: int = 0,
) -> None:
    """Configures a specified result logger for spectroscopy mode.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which result logger to configure - there is one
                           result logger per channel

      result_length (int): number of results to be returned by the result logger

      num_averages (optional int): number of averages, will be rounded to 2^n

      averaging_mode (optional int): select the averaging order of the result, with 0 = cyclic
                                     and 1 = sequential.

    """

    result_path = f"/{device_id}/qachannels/{channel_index}/spectroscopy/result/"
    daq.setInt(result_path + "length", result_length)
    daq.setInt(result_path + "averages", num_averages)
    daq.setInt(result_path + "mode", averaging_mode)


def configure_result_logger_for_readout(
    daq,
    device_id: str,
    channel_index: int,
    result_source: str,
    result_length: int,
    num_averages: int = 1,
    averaging_mode: int = 0,
) -> None:
    """Configures a specified result logger for readout mode.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which result logger to configure - there is one
                           result logger per channel

      result_source (str): string-based tag to select the result source
                           in readout mode, e.g. "result_of_integration"
                           or "result_of_discrimination".

      result_length (int): number of results to be returned by the result logger

      num_averages (optional int): number of averages, will be rounded to 2^n

      averaging_mode (optional int): select the averaging order of the result, with 0 = cyclic
                                     and 1 = sequential.

    """

    result_path = f"/{device_id}/qachannels/{channel_index}/readout/result/"
    daq.setInt(result_path + "length", result_length)
    daq.setInt(result_path + "averages", num_averages)
    daq.setString(result_path + "source", result_source)
    daq.setInt(result_path + "mode", averaging_mode)


def enable_result_logger(daq, device_id: str, channel_index: int, mode: str) -> None:
    """Resets and enables a specified result logger.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which result logger to enable - there is one
                           result logger per channel

      mode (str): select between "spectroscopy" and "readout" mode.

    """

    enable_path = f"/{device_id}/qachannels/{channel_index}/{mode}/result/enable"
    # reset the result logger if some old measurement is still running
    if daq.getInt(enable_path) != 0:
        daq.setInt(enable_path, 0)
        assert_node_changes_to_expected_value(daq, enable_path, 0)
    daq.setInt(enable_path, 1)
    assert_node_changes_to_expected_value(daq, enable_path, 1)


def get_result_logger_data(
    daq, device_id: str, channel_index: int, mode: str, time_out: float = 1.0
) -> np.array:
    """Waits until a specified result logger finished recording and returns the measured data.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which result logger to query results from - there
                           is one result logger per channel

      mode (str): select between "spectroscopy" and "readout" mode.

      time_out (optional float): maximum time to wait for data in seconds

    Returns:

      result (array): array containing the result logger data

    """

    sleep_time = 0.05
    num_loops = int(time_out / sleep_time)
    assert_node_changes_to_expected_value(
        daq,
        f"/{device_id}/qachannels/{channel_index}/{mode}/result/enable",
        0,
        sleep_time=sleep_time,
        max_repetitions=num_loops,
    )
    daq.sync()

    data = daq.get(
        f"/{device_id}/qachannels/{channel_index}/{mode}/result/data/*/wave",
        flat=True,
    )

    result = np.array([(lambda x: x[0]["vector"])(d) for d in data.values()])
    return result


def configure_channel(
    daq,
    device_id: str,
    channel_index: int,
    input_range: int,
    output_range: int,
    center_frequency: float,
    mode: str,
) -> None:
    """Configures the RF input and output of a specified channel.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying which channel to configure

      input_range (int): maximal range of the signal input power in dbM

      output_range (int): maximal range of the signal output power in dbM

      center_frequency (float): center Frequency of the analysis band

      mode (str): select between "spectroscopy" and "readout" mode.

    """

    path = f"/{device_id}/qachannels/{channel_index}/"

    daq.setInt(path + "input/range", input_range)
    daq.setInt(path + "output/range", output_range)

    daq.setDouble(path + "centerfreq", center_frequency)

    daq.setString(path + "mode", mode)


def configure_sequencer_triggering(
    daq,
    device_id: str,
    channel_index: int,
    aux_trigger: str,
    play_pulse_delay: float = 0.0,
) -> None:
    """Configures the triggering of a specified sequencer.

    Arguments:

      daq (ziDAQServer): instance of a Zurich Instruments API session connected to a Data Server.
                         The device with identifier device_id is assumed to already be
                         connected to this instance.

      device_id (str): SHFQA device identifier, e.g. `dev12004` or 'shf-dev12004'

      channel_index (int): index specifying on which sequencer to configure the
                           triggering - there is one sequencer per channel

      aux_trigger (string): alias for the trigger used in the sequencer.
                            For a list of available values use
                            daq.help(f"/{device_id}/qachannels/0/generator/auxtriggers/0/channel")

      play_pulse_delay (optional float): delay in seconds before the start of waveform playback

    """

    daq.setString(
        f"/{device_id}/qachannels/{channel_index}/generator/auxtriggers/0/channel",
        aux_trigger,
    )
    daq.setDouble(
        f"/{device_id}/qachannels/{channel_index}/generator/delay",
        play_pulse_delay,
    )
