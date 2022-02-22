"""
Zurich Instruments LabOne Python API Utility functions for SHFSG.
"""

import time

from zhinst.utils import convert_awg_waveform, wait_for_state_change
from zhinst.ziPython import AwgModule, ziDAQServer

SHFSG_MAX_SIGNAL_GENERATOR_WAVEFORM_LENGTH = 98304
SHFSG_SAMPLING_FREQUENCY = 2e9


def load_sequencer_program(
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    sequencer_program: str,
    *,
    awg_module: AwgModule = None,
    timeout: float = 10,
) -> None:
    """Compiles and loads a program to a specified AWG core.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        sequencer_program: Sequencer program to be uploaded.
        awg_module: AWG module instance used to interact with the
            sequencer. If none is provided, a new local instance will be
            created. (default = None)
        timeout: maximum time to wait for the compilation in seconds.
            (default = 10)
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
    awg_module = daq.awgModule() if awg_module is None else awg_module
    awg_module.set("device", device_id)
    awg_module.set("sequencertype", "sg")
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


def enable_sequencer(
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    *,
    single: bool = True,
) -> None:
    """Starts the sequencer of a specific channel.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        single: Flag if the sequencer should run in single mode.
    """
    sequencer_path = f"/{device_id}/sgchannels/{channel_index}/awg/"
    daq.setInt(
        sequencer_path + "single",
        int(single),
    )
    daq.syncSetInt(sequencer_path + "enable", 1)
    wait_for_state_change(daq, sequencer_path + "enable", 1)


def upload_commandtable(
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    command_table: str,
) -> None:
    """Uploads a command table in the form of a string to the appropriate channel

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which channel to upload the command
            table to.
        command_table: The command table to be uploaded.
    """
    # upload command table
    daq.setVector(
        f"/{device_id}/sgchannels/{channel_index}/awg/commandtable/data",
        command_table,
    )


def write_to_waveform_memory(
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    waveforms: dict,
) -> None:
    """Writes waveforms to the waveform memory of a specified sequencer.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        waveforms (dict): Dictionary of waveforms, the key specifies the
            waveform index to which to write the waveforms.

    """
    waveforms_path = f"/{device_id}/sgchannels/{channel_index}/awg/waveform/waves/"
    settings = []

    for slot, waveform in waveforms.items():
        wave_raw = convert_awg_waveform(waveform)
        settings.append((waveforms_path + f"{slot}", wave_raw))

    daq.set(settings)


def configure_marker_and_trigger(
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    *,
    trigger_in_source: str,
    trigger_in_slope: str,
    marker_out_source: str,
) -> None:
    """Configures the trigger inputs and marker outputs of a specified AWG core.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        trigger_in_source: Alias for the trigger input used by the
            sequencer. For a list of available values use:
            daq.help(f"/{dev_id}/sgchannels/{channel_index}/awg/auxtriggers/0/channel")
        tringger_in_slope: Alias for the slope of the input trigger used
            by sequencer. For a list of available values use
            daq.help(f"/{dev_id}/sgchannels/{channel_index}/awg/auxtriggers/0/slope")
        marker_out_source: Alias for the marker output source used by the
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
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    *,
    enable: int,
    output_range: int,
    center_frequency: float,
    rflf_path: int,
) -> None:
    """Configures the RF input and output of a specified channel.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        output_range: Maximal range of the signal output power in dbM.
        center_frequency: Center Frequency before modulation.
        rflf_path: Switch between RF and LF paths.
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
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    *,
    enable: int,
    osc_index: int = 0,
    osc_frequency: float = 100e6,
    phase: float = 0.0,
    global_amp: float = 0.5,
    gains: tuple = (1.0, -1.0, 1.0, 1.0),
    sine_generator_index: int = 0,
) -> None:
    """Configure the pulse modulation.

    Configures the sine generator to digitally modulate the AWG output, for
    generating single sideband AWG signals.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        enable: Enables modulation.
        osc_index: Selects which oscillator to use.
        osc_frequency: Oscillator frequency used to modulate the AWG
            outputs. (default = 100e6)
        phase: Sets the oscillator phase. (default = 0.0)
        global_amp: Global scale factor for the AWG outputs. (default = 0.5)
        gains: Sets the four amplitudes used for single sideband
            generation. default values correspond to upper sideband with a
            positive oscillator frequency. (default = (1.0, -1.0, 1.0, 1.0))
        sine_generator_index: Selects which sine generator to use on a given
            channel.
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
    daq: ziDAQServer,
    device_id: str,
    channel_index: int,
    *,
    enable: int,
    osc_index: int = 0,
    osc_frequency: float = 100e6,
    phase: float = 0.0,
    gains: tuple = (0.0, 1.0, 1.0, 0.0),
    sine_generator_index: int = 0,
) -> None:
    """Configures the sine generator output of a specified channel.

    Configures the sine generator output of a specified channel for generating
    continuous wave signals without the AWG.

    Args:
        daq: Instance of a Zurich Instruments API session connected to a Data
            Server. The device with identifier device_id is assumed to already
            be connected to this instance.
        device_id: SHFSG device identifier, e.g. `dev12004` or 'shf-dev12004'.
        channel_index: Index specifying which sequencer to enable - there
            is one sequencer per channel.
        enable: Enables the sine generator output.
        osc_index: Selects which oscillator to use.
        osc_frequency: Oscillator frequency used by the sine generator.
            (default = 100e6)
        phase: Sets the oscillator phase. (default = 0.0)
        gains: Sets the four amplitudes used for single sideband.
            generation. default values correspond to upper sideband with a
            positive oscillator frequency. gains are set in this order:
            I/sin, I/cos, Q/sin, Q/cos
            (default = (0.0, 1.0, 1.0, 0.0))
        sine_generator_index: Selects which sine generator to use on a given
            channel.
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
