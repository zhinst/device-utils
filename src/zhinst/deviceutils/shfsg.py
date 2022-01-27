"""
Zurich Instruments LabOne Python API Utility functions for SHFSG.
"""

import time

from zhinst.utils import wait_for_state_change
from zhinst.utils import convert_awg_waveform

SHFSG_MAX_SIGNAL_GENERATOR_WAVEFORM_LENGTH = 98304
SHFSG_SAMPLING_FREQUENCY = 2e9


def load_sequencer_program(
    daq,
    device_id: str,
    channel_index: int,
    sequencer_program: str,
    command_table: str = None,
    awg_module=None,
    timeout: float = 10,
) -> None:
    """Compiles and loads a program to a specified AWG core.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        sequencer_program (str): sequencer program to be uploaded
        command_table (str): command table to be uploaded. (default = None)
        awg_module (AwgModule): awg module instance used to interact with the
            sequencer. If none is provided, a new local instance will be
            created. (default = None)
        timeout (float): maximum time to wait for the compilation in seconds. (default = 10)
    """

    # start by resetting the sequencer
    daq.syncSetInt(
        f"/{device_id}/sgchannels/{channel_index}/awg/reset",
        1,
    )
    wait_for_state_change(
        daq,
        f"/{device_id}/sgchannels/{channel_index}/awg/ready",
        0,
        timeout=timeout,
    )

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
        if time.time() - t_start > timeout:
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
                    {timeout} s,\n"
                + statusstring
            )
        else:
            raise RuntimeError(
                f"Failed to compile program for channel {channel_index},\n"
                + statusstring
            )

    # wait until the device becomes ready after program upload
    wait_for_state_change(
        daq,
        f"/{device_id}/sgchannels/{channel_index}/awg/ready",
        1,
        timeout=timeout,
    )

    # upload command table after sequencer upload has finished
    if command_table is not None:
        daq.setVector(
            f"/{device_id}/sgchannels/{channel_index}/awg/commandtable/data",
            command_table,
        )


def enable_sequencer(
    daq,
    device_id: str,
    channel_index: int,
    single: int,
) -> None:
    """Starts the sequencer of a specific channel.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        single (int): 1 - disable sequencer after finishing execution
                      0 - restart sequencer after finishing execution
    """
    sequencer_path = f"/{device_id}/sgchannels/{channel_index}/awg/"
    daq.setInt(
        sequencer_path + "single",
        single,
    )
    daq.syncSetInt(sequencer_path + "enable", 1)
    wait_for_state_change(daq, sequencer_path + "enable", 1)


def write_to_waveform_memory(
    daq,
    device_id: str,
    channel_index: int,
    waveforms: dict,
) -> None:
    """Writes waveforms to the waveform memory of a specified sequencer.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        waveforms (dict): dictionary of waveforms, the key specifies the waveform index to
            which to write the waveforms

    """
    waveforms_path = f"/{device_id}/sgchannels/{channel_index}/awg/waveform/waves/"
    settings = []

    for slot, waveform in waveforms.items():
        wave_raw = convert_awg_waveform(waveform)
        settings.append((waveforms_path + f"{slot}", wave_raw))

    daq.set(settings)


def configure_marker_and_trigger(
    daq,
    device_id: str,
    channel_index: int,
    trigger_in_source: str,
    trigger_in_slope: str,
    marker_out_source: str,
) -> None:
    """Configures the trigger inputs and marker outputs of a specified AWG core.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        trigger_in_source (str): alias for the trigger input used by the
            sequencer. For a list of available values use:
            daq.help(f"/{dev_id}/sgchannels/{channel_index}/awg/auxtriggers/0/channel")
        tringger_in_slope (str): alias for the slope of the input trigger used
            by sequencer. For a list of available values use
            daq.help(f"/{dev_id}/sgchannels/{channel_index}/awg/auxtriggers/0/slope")
        marker_out_source (str): alias for the marker output source used by the
            sequencer. For a list of available values use
            daq.help(f"/{dev_id}/sgchannels/{channel_index}/marker/source")
    """

    # Trigger input
    settings = []
    settings.append(
        (
            f"/{device_id}/sgchannels/{channel_index}/awg/auxtriggers/0/channel",
            trigger_in_source,
        )
    )
    settings.append(
        (
            f"/{device_id}/sgchannels/{channel_index}/awg/auxtriggers/0/slope",
            trigger_in_slope,
        )
    )

    # Marker output
    settings.append(
        (
            f"/{device_id}/sgchannels/{channel_index}/marker/source",
            marker_out_source,
        )
    )
    daq.set(settings)


def configure_channel(
    daq,
    device_id: str,
    channel_index: int,
    enable: int,
    output_range: int,
    center_frequency: float,
    rflf_path: int,
) -> None:
    """Configures the RF input and output of a specified channel.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        output_range (int): maximal range of the signal output power in dbM
        center_frequency (float): center Frequency before modulation
        rflf_path (int): switch between RF and LF paths
    """

    path = f"/{device_id}/sgchannels/{channel_index}/"
    settings = []

    settings.append((path + "output/range", output_range))
    settings.append((path + "output/rflfpath", rflf_path))
    if rflf_path == 1:
        synth = daq.getInt(path + "synthesizer")
        settings.append(
            (f"/{device_id}/synthesizers/{synth}/centerfreq", center_frequency)
        )
    elif rflf_path == 0:
        settings.append((path + "digitalmixer/centerfreq", center_frequency))
    settings.append((path + "output/on", enable))

    daq.set(settings)


def configure_pulse_modulation(
    daq,
    device_id: str,
    channel_index: int,
    enable: int,
    osc_index: int,
    osc_frequency: float = 100e6,
    phase: float = 0.0,
    global_amp: float = 0.5,
    gains: tuple = (1.0, -1.0, 1.0, 1.0),
    sine_generator_index: int = 0,
) -> None:
    """Configure the pulse modulation

    Configures the sine generator to digitally modulate the AWG output, for
    generating single sideband AWG signals

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        enable (int): enables modulation
        osc_index (int): selects which oscillator to use
        osc_frequency (float): oscillator frequency used to modulate the AWG
            outputs. (default = 100e6)
        phase (float): sets the oscillator phase. (default = 0.0)
        global_amp (float): global scale factor for the AWG outputs. (default = 0.5)
        gains (tuple): sets the four amplitudes used for single sideband
            generation. default values correspond to upper sideband with a
            positive oscillator frequency. (default = (1.0, -1.0, 1.0, 1.0))
        sine_generator_index (int): selects which sine generator to use on a given channel
    """

    path = f"/{device_id}/sgchannels/{channel_index}/"
    settings = []

    settings.append((path + f"sines/{sine_generator_index}/oscselect", osc_index))
    settings.append((path + f"sines/{sine_generator_index}/phaseshift", phase))
    settings.append((path + f"oscs/{osc_index}/freq", osc_frequency))
    settings.append((path + "awg/modulation/enable", enable))
    settings.append((path + "awg/outputamplitude", global_amp))
    settings.append((path + "awg/outputs/0/gains/0", gains[0]))
    settings.append((path + "awg/outputs/0/gains/1", gains[1]))
    settings.append((path + "awg/outputs/1/gains/0", gains[2]))
    settings.append((path + "awg/outputs/1/gains/1", gains[3]))

    daq.set(settings)


def configure_sine_generation(
    daq,
    device_id: str,
    channel_index: int,
    enable: int,
    osc_index: int,
    osc_frequency: float = 100e6,
    phase: float = 0.0,
    gains: tuple = (0.0, 1.0, 1.0, 0.0),
    sine_generator_index: int = 0,
) -> None:
    """Configures the sine generator output of a specified channel.

    Configures the sine generator output of a specified channel for generating
    continuous wave signals without the AWG.

    Args:
        daq (ziDAQServer): instance of a Zurich Instruments API session
            connected to a Data Server. The device with identifier device_id is
            assumed to already be connected to this instance.
        device_id (str): SHFSG device identifier, e.g. `dev12050` or'shf-dev12050'
        channel_index (int): index specifying which sequencer to enable - there
            is one sequencer per channel
        enable (int): enables the sine generator output
        osc_index (int): selects which oscillator to use
        osc_frequency (float): oscillator frequency used by the sine generator
            (default = 100e6)
        phase (float): sets the oscillator phase. (default = 0.0)
        gains (tuple): sets the four amplitudes used for single sideband
            generation. default values correspond to upper sideband with a
            positive oscillator frequency. gains are set in this order:
            I/sin, I/cos, Q/sin, Q/cos
            (default = (0.0, 1.0, 1.0, 0.0))
        sine_generator_index (int): selects which sine generator to use on a given channel
    """

    path = f"/{device_id}/sgchannels/{channel_index}/sines/{sine_generator_index}/"
    settings = []

    settings.append((path + "i/enable", enable))
    settings.append((path + "q/enable", enable))
    settings.append((path + "i/sin/amplitude", gains[0]))
    settings.append((path + "i/cos/amplitude", gains[1]))
    settings.append((path + "q/sin/amplitude", gains[2]))
    settings.append((path + "q/cos/amplitude", gains[3]))
    settings.append((path + "oscselect", osc_index))
    settings.append(
        (
            f"/{device_id}/sgchannels/{channel_index}/oscs/{osc_index}/freq",
            osc_frequency,
        )
    )
    settings.append((path + "phaseshift", phase))

    daq.set(settings)
