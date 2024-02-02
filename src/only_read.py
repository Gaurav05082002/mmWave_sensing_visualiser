import argparse
import csv
import math
import os
import time
from inspect import trace
from operator import add
from time import sleep
from turtle import pd

import matplotlib.pyplot as plt
import numpy as np
import serial
from dotenv import load_dotenv

# import fft
from scipy.fftpack import fft
# smooth

load_dotenv(".env")
os_name = os.environ.get("OS")
framePeriodicity = 0
configs = {
    "pointcloud": "Configurations/pointcloud_configuration.cfg",
    "macro": "Configurations/macro_5fps.cfg",
    "micro": "Configurations/micro_2fps.cfg",
}
#configFileName = configs["pointcloud"]
# CLIport = {}
# Dataport = {}
byteBuffer = np.zeros(2**15, dtype="uint8")
byteBufferLength = 0
rangeAzimuthHeatMapGridInit = 0
xlin, ylin = [], []
NUM_ANGLE_BINS = 64
range_depth = 10
range_width = 5
changes_happening = 0
change_conf = False

header = [
    "Date",
    "Time",
    "numObj",
    "rangeIdx",
    "range",
    "dopplerIdx",
    "doppler",
    "peakVal",
    "x",
    "y",
    "z",
    "rp",
    "noiserp",
    "zi",
    "rangeDoppler",
    "rangeArray",
    "dopplerArray",
    "interFrameProcessingTime",
    "transmitOutputTime",
    "interFrameProcessingMargin",
    "interChirpProcessingMargin",
    "activeFrameCPULoad",
    "interFrameCPULoad",
]


def file_create():
    filename = os.path.abspath("")
    if os_name == "Windows_NT":
        filename += time.strftime("\%Y%m%d_%H%M%S")
    elif os_name == "Ubuntu":
        filename += time.strftime("/%Y%m%d_%H%M%S")
    filename += ".csv"
    with open(filename, "w") as f:
        csv.DictWriter(f, fieldnames=header).writeheader()

    return filename


# ------------------------------------------------------------------


# Function to configure the serial ports and send the data from
# the configuration file to the radar
def serialConfig(configFileName):
    global CLIport
    global Dataport

    CLIport = ""
    Dataport = ""
    # Open the serial ports for the configuration and the data ports

    # Raspberry pi
    if os_name == "Ubuntu":
        CLIport = serial.Serial("/dev/ttyACM0", 115200)
        Dataport = serial.Serial("/dev/ttyACM1", 921600)

    elif os_name == "Windows_NT":
        CLIport = serial.Serial("COM3", 115200)
        Dataport = serial.Serial("COM4", 921600)

    # Read the configuration file and send it to the board
    config = [line.rstrip("\r\n") for line in open(configFileName)]
    for i in config:
        print(i)
        CLIport.write((i + "\n").encode())
        time.sleep(0.01)

    return CLIport, Dataport


# ------------------------------------------------------------------


# Function to parse the data inside the configuration file
def parseConfigFile(configFileName):
    global framePeriodicity
    configParameters = (
        {}
    )  # Initialize an empty dictionary to store the configuration parameters

    # Read the configuration file and send it to the board
    config = [line.rstrip("\r\n") for line in open(configFileName)]
    for i in config:
        # Split the line
        splitWords = i.split(" ")

        # Hard code the number of antennas, change if other configuration is used
        numRxAnt = 6
        numTxAnt = 2

        # Get the information about the profile configuration
        if "profileCfg" in splitWords[0]:
            startFreq = int(float(splitWords[2]))
            idleTime = int(splitWords[3])
            rampEndTime = float(splitWords[5])
            freqSlopeConst = float(splitWords[8])
            numAdcSamples = int(splitWords[10])
            numAdcSamplesRoundTo2 = 1

            while numAdcSamples > numAdcSamplesRoundTo2:
                numAdcSamplesRoundTo2 = numAdcSamplesRoundTo2 * 2

            digOutSampleRate = int(splitWords[11])

        # Get the information about the frame configuration
        elif "frameCfg" in splitWords[0]:
            chirpStartIdx = int(splitWords[1])
            chirpEndIdx = int(splitWords[2])
            numLoops = int(splitWords[3])
            numFrames = int(splitWords[4])
            framePeriodicity = int(float(splitWords[5]))

    # Combine the read data to obtain the configuration parameters
    numChirpsPerFrame = (chirpEndIdx - chirpStartIdx + 1) * numLoops
    configParameters["numDopplerBins"] = numChirpsPerFrame / numTxAnt
    configParameters["numRangeBins"] = numAdcSamplesRoundTo2
    configParameters["rangeResolutionMeters"] = (3e8 * digOutSampleRate * 1e3) / (
        2 * freqSlopeConst * 1e12 * numAdcSamples
    )
    configParameters["rangeIdxToMeters"] = (3e8 * digOutSampleRate * 1e3) / (
        2 * freqSlopeConst * 1e12 * configParameters["numRangeBins"]
    )
    configParameters["dopplerResolutionMps"] = 3e8 / (
        2
        * startFreq
        * 1e9
        * (idleTime + rampEndTime)
        * 1e-6
        * configParameters["numDopplerBins"]
        * numTxAnt
    )
    configParameters["maxRange"] = (300 * 0.9 * digOutSampleRate) / (
        2 * freqSlopeConst * 1e3
    )
    configParameters["maxVelocity"] = 3e8 / (
        4 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * numTxAnt
    )

    return configParameters


# ------------------------------------------------------------------

# Helper methods for processing


def tensor_f(vec1, vec2):
    t = []
    for r in range(0, len(vec1)):
        t.append(np.multiply(np.array(vec2), vec1[r]))
    return t


def meshgrid(xvec, yvec):
    x = []
    y = []
    for r in range(0, len(yvec)):
        for c in range(0, len(xvec)):
            x.append(xvec[c])
            y.append(yvec[r])
    return [x, y]


def reshape_rowbased(vec, rows, cols):
    t = []
    start = 0
    for r in range(0, rows):
        row = vec[start : start + cols]
        t.append(row)
        start += cols
    return t


def change_conf_callback():
    global CLIport, Dataport, configParameters, configFileName, byteBuffer, byteBufferLength
    byteBuffer = np.zeros(2**15, dtype="uint8")
    byteBufferLength = 0
    print(
        "############################ changing configuration to macro ##########################"
    )
    time.sleep(2)
    configFileName = "Configurations/macro_7fps.cfg"
    CLIport, Dataport = serialConfig(configFileName)
    configParameters = parseConfigFile(configFileName)


def processDetectedPoints(byteBuffer, idX, configParameters):
    global configFileName

    # word array to convert 4 bytes to a 16-bit number
    word = [1, 2**8]
    tlv_numObj = np.matmul(byteBuffer[idX : idX + 2], word)
    idX += 2
    tlv_xyzQFormat = 2 ** np.matmul(byteBuffer[idX : idX + 2], word)
    idX += 2

    # Initialize the arrays
    rangeIdx = np.zeros(tlv_numObj, dtype="int16")
    dopplerIdx = np.zeros(tlv_numObj, dtype="int16")
    peakVal = np.zeros(tlv_numObj, dtype="int16")
    x = np.zeros(tlv_numObj, dtype="int16")
    y = np.zeros(tlv_numObj, dtype="int16")
    z = np.zeros(tlv_numObj, dtype="int16")

    for objectNum in range(tlv_numObj):
        # Read the data for each object
        rangeIdx[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2
        dopplerIdx[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2
        peakVal[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2
        x[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2
        y[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2
        z[objectNum] = np.matmul(byteBuffer[idX : idX + 2], word)
        idX += 2

    # Make the necessary corrections and calculate the rest of the data
    rangeVal = rangeIdx * configParameters["rangeIdxToMeters"]
    dopplerIdx[dopplerIdx > (configParameters["numDopplerBins"] / 2 - 1)] = (
        dopplerIdx[dopplerIdx > (configParameters["numDopplerBins"] / 2 - 1)] - 65535
    )
    dopplerVal = dopplerIdx * configParameters["dopplerResolutionMps"]
    x = x / tlv_xyzQFormat
    y = y / tlv_xyzQFormat
    z = z / tlv_xyzQFormat

    # Store the data in the detObj dictionary
    detObj = {
        "numObj": tlv_numObj,
        "rangeIdx": list(rangeIdx),
        "range": list(rangeVal),
        "dopplerIdx": list(dopplerIdx),
        "doppler": list(dopplerVal),
        "peakVal": list(peakVal),
        "x": list(x),
        "y": list(y),
        "z": list(z),
    }
    return detObj


def processRangeNoiseProfile(byteBuffer, idX, detObj, configParameters, isRangeProfile):
    traceidX = 0
    if isRangeProfile:
        traceidX = 0
    else:
        traceidX = 2
    numrp = 2 * configParameters["numRangeBins"]
    rp = byteBuffer[idX : idX + numrp]

    rp = list(map(add, rp[0:numrp:2], list(map(lambda x: 256 * x, rp[1:numrp:2]))))
    rp_x = (
        np.array(range(configParameters["numRangeBins"]))
        * configParameters["rangeIdxToMeters"]
    )
    idX += numrp
    if traceidX == 0:
        noiseObj = {"rp": rp}
        return noiseObj
    elif traceidX == 2:
        noiseObj = {"noiserp": rp}
        return noiseObj


def processAzimuthHeatMap(byteBuffer, idX, configParameters):
    numTxAnt = 2
    numRxAnt = 4
    numBytes = numRxAnt * numTxAnt * configParameters["numRangeBins"] * 4
    q = byteBuffer[idX : idX + numBytes]
    idX += numBytes
    q_rows = numTxAnt * numRxAnt
    q_cols = configParameters["numRangeBins"]
    q_idx = 0
    QQ = []
    NUM_ANGLE_BINS = 64
    for i in range(0, q_cols):
        real = np.zeros(NUM_ANGLE_BINS)
        img = np.zeros(NUM_ANGLE_BINS)
        for j in range(0, q_rows):
            real[j] = q[q_idx + 1] * 256 + q[q_idx]
            if real[j] > 32767:
                real[j] = real[j] - 65536
            img[j] = q[q_idx + 3] * 256 + q[q_idx + 2]
            if img[j] > 32767:
                img[j] = img[j] - 65536
            q_idx = q_idx + 4
        fft.transform(real, img)
        for ri in range(0, NUM_ANGLE_BINS):
            real[ri] = int(math.sqrt(real[ri] * real[ri] + img[ri] * img[ri]))

        QQ.append(
            [
                y
                for x in [
                    real[int(NUM_ANGLE_BINS / 2) :],
                    real[0 : int(NUM_ANGLE_BINS / 2)],
                ]
                for y in x
            ]
        )
    fliplrQQ = []
    for tmpr in range(0, len(QQ)):
        fliplrQQ.append(QQ[tmpr][1:].reverse())
    global rangeAzimuthHeatMapGridInit
    if rangeAzimuthHeatMapGridInit == 0:
        angles_rad = np.multiply(
            np.arange(-NUM_ANGLE_BINS / 2 + 1, NUM_ANGLE_BINS / 2, 1),
            2 / NUM_ANGLE_BINS,
        )
        theta = []
        for ang in angles_rad:
            theta.append(math.asin(ang))
        range_val = np.multiply(
            np.arange(0, configParameters["numRangeBins"], 1),
            configParameters["rangeIdxToMeters"],
        )
        sin_theta = []
        cos_theta = []
        for t in theta:
            sin_theta.append(math.sin(t))
            cos_theta.append(math.cos(t))
        posX = tensor_f(range_val, sin_theta)
        posY = tensor_f(range_val, cos_theta)

        global xlin, ylin
        xlin = np.arange(-range_width, range_width, 2 * range_width / 99)
        if len(xlin) < 100:
            xlin = np.append(xlin, range_width)
        ylin = np.arange(0, range_depth, 1.0 * range_depth / 99)
        if len(ylin) < 100:
            ylin = np.append(ylin, range_depth)

        xiyi = meshgrid(xlin, ylin)
        rangeAzimuthHeatMapGridInit = 1

    zi = fliplrQQ
    zi = reshape_rowbased(zi, len(ylin), len(xlin))
    heatObj = {"zi": zi}
    return heatObj


def processRangeDopplerHeatMap(byteBuffer, idX):
    # Get the number of bytes to read
    numBytes = (
        int(configParameters["numDopplerBins"])
        * int(configParameters["numRangeBins"])
        * 2
    )
    # Convert the raw data to int16 array
    payload = byteBuffer[idX : idX + numBytes]
    idX += numBytes
    # rangeDoppler = math.add(
    #     math.subset(rangeDoppler, math.index(math.range(0, numBytes, 2))),
    #     math.multiply(math.subset(rangeDoppler, math.index(math.range(1, numBytes, 2))), 256)
    # );

    rangeDoppler = list(
        map(
            add,
            payload[0:numBytes:2],
            list(map(lambda x: 256 * x, payload[1:numBytes:2])),
        )
    )  # wrong implementation. Need to update the range doppler at range index

    # rangeDoppler = payload.view(dtype=np.int16)
    # Some frames have strange values, skip those frames
    # TO DO: Find why those strange frames happen
    # if np.max(rangeDoppler) > 10000:
    #     return 0

    # Convert the range doppler array to a matrix
    rangeDoppler = np.reshape(
        rangeDoppler,
        (int(configParameters["numDopplerBins"]), configParameters["numRangeBins"]),
        "F",
    )  # Fortran-like reshape
    rangeDoppler = np.append(
        rangeDoppler[int(len(rangeDoppler) / 2) :],
        rangeDoppler[: int(len(rangeDoppler) / 2)],
        axis=0,
    )

    dopplerM = []
    rangeDoppler_list = list(rangeDoppler)
    for e in rangeDoppler_list:
        dopplerM.append(list(e))

    #
    # # Generate the range and doppler arrays for the plot
    rangeArray = (
        np.array(range(configParameters["numRangeBins"]))
        * configParameters["rangeIdxToMeters"]
    )
    dopplerArray = np.multiply(
        np.arange(
            -configParameters["numDopplerBins"] / 2,
            configParameters["numDopplerBins"] / 2,
        ),
        configParameters["dopplerResolutionMps"],
    )  # This is dopplermps from js.
    dopplerObj = {
        "rangeDoppler": dopplerM,
        "rangeArray": list(rangeArray),
        "dopplerArray": list(dopplerArray),
    }
    return dopplerObj


def processStatistics(byteBuffer, idX):
    word = [1, 2**8, 2**16, 2**24]
    interFrameProcessingTime = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4
    transmitOutputTime = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4
    interFrameProcessingMargin = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4
    interChirpProcessingMargin = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4
    activeFrameCPULoad = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4

    interFrameCPULoad = np.matmul(byteBuffer[idX : idX + 4], word)
    idX += 4

    statisticsObj = {
        "interFrameProcessingTime": interFrameProcessingTime,
        "transmitOutputTime": transmitOutputTime,
        "interFrameProcessingMargin": interFrameProcessingMargin,
        "interChirpProcessingMargin": interChirpProcessingMargin,
        "activeFrameCPULoad": activeFrameCPULoad,
        "interFrameCPULoad": interFrameCPULoad,
    }
    return statisticsObj


def buffer_flush(idX, byteBufferLength, totalPacketLen):
    if 0 < idX < byteBufferLength:
        shiftSize = totalPacketLen

        byteBuffer[: byteBufferLength - shiftSize] = byteBuffer[
            shiftSize:byteBufferLength
        ]
        byteBuffer[byteBufferLength - shiftSize :] = np.zeros(
            len(byteBuffer[byteBufferLength - shiftSize :]), dtype="uint8"
        )
        byteBufferLength = byteBufferLength - shiftSize

        # Check that there are no errors with the buffer length
        if byteBufferLength < 0:
            byteBufferLength = 0


def readAndParseData16xx(Dataport, configParameters, filename):
    global byteBuffer, byteBufferLength, framePeriodicity, changes_happening, change_conf, configFileName
    finalObj = {"Date": time.strftime("%d/%m/%Y"), "Time": time.strftime("%H%M%S")}
    # Constants
    OBJ_STRUCT_SIZE_BYTES = 12
    BYTE_VEC_ACC_MAX_SIZE = 2**15
    MMWDEMO_UART_MSG_DETECTED_POINTS = 1
    MMWDEMO_UART_MSG_RANGE_PROFILE = 2
    MMWDEMO_OUTPUT_MSG_NOISE_PROFILE = 3
    MMWDEMO_OUTPUT_MSG_AZIMUT_STATIC_HEAT_MAP = 4
    MMWDEMO_OUTPUT_MSG_RANGE_DOPPLER_HEAT_MAP = 5
    MMWDEMO_OUTPUT_MSG_STATS = 6
    maxBufferSize = 2**15
    magicWord = [2, 1, 4, 3, 6, 5, 8, 7]

    # Initialize variables
    magicOK = 0  # Checks if magic number has been read
    dataOK = 0  # Checks if the data has been read correctly
    frameNumber = 0
    detObj = {}
    tlv_type = 0

    readBuffer = Dataport.read(Dataport.in_waiting)
    byteVec = np.frombuffer(readBuffer, dtype="uint8")
    byteCount = len(byteVec)
    # Check that the buffer is not full, and then add the data to the buffer
    if (byteBufferLength + byteCount) < maxBufferSize:
        byteBuffer[byteBufferLength : byteBufferLength + byteCount] = byteVec[
            :byteCount
        ]
        byteBufferLength = byteBufferLength + byteCount

    # Check that the buffer has some data
    if byteBufferLength > 16:
        # Check for all possible locations of the magic word
        possibleLocs = np.where(byteBuffer == magicWord[0])[0]

        # Confirm that is the beginning of the magic word and store the index in startIdx
        startIdx = []
        for loc in possibleLocs:
            check = byteBuffer[loc : loc + 8]
            if np.all(check == magicWord):
                startIdx.append(loc)

        # Check that startIdx is not empty
        if startIdx:
            # Remove the data before the first start index
            if 0 < startIdx[0] < byteBufferLength:
                byteBuffer[: byteBufferLength - startIdx[0]] = byteBuffer[
                    startIdx[0] : byteBufferLength
                ]
                byteBuffer[byteBufferLength - startIdx[0] :] = np.zeros(
                    len(byteBuffer[byteBufferLength - startIdx[0] :]), dtype="uint8"
                )
                byteBufferLength = byteBufferLength - startIdx[0]

            # Check that there have no errors with the byte buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0

            # word array to convert 4 bytes to a 32-bit number
            word = [1, 2**8, 2**16, 2**24]

            # Read the total packet length
            totalPacketLen = np.matmul(byteBuffer[12 : 12 + 4], word)

            # Check that all the packet has been read
            if (byteBufferLength >= totalPacketLen) and (byteBufferLength != 0):
                magicOK = 1

    # If magicOK is equal to 1 then process the message
    if magicOK:
        # word array to convert 4 bytes to a 32-bit number
        word = [1, 2**8, 2**16, 2**24]

        # Initialize the pointer index
        idX = 0

        # Read the header
        magicNumber = byteBuffer[idX : idX + 8]
        idX += 8
        version = format(np.matmul(byteBuffer[idX : idX + 4], word), "x")
        idX += 4
        totalPacketLen = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        platform = format(np.matmul(byteBuffer[idX : idX + 4], word), "x")
        idX += 4
        frameNumber = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        timeCpuCycles = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        numDetectedObj = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        numTLVs = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        subFrameNumber = np.matmul(byteBuffer[idX : idX + 4], word)
        idX += 4
        # Read the TLV messages
        for tlvIdx in range(numTLVs):
            # word array to convert 4 bytes to a 32 bit number
            word = [1, 2**8, 2**16, 2**24]

            # Check the header of the TLV message
            tlv_type = np.matmul(byteBuffer[idX : idX + 4], word)
            idX += 4
            tlv_length = np.matmul(byteBuffer[idX : idX + 4], word)
            idX += 4
            # Read the data depending on the TLV message
            if tlv_type == MMWDEMO_UART_MSG_DETECTED_POINTS:
                detObj = processDetectedPoints(byteBuffer, idX, configParameters)
                finalObj.update(detObj)
            elif tlv_type == MMWDEMO_UART_MSG_RANGE_PROFILE:
                noiseObj = processRangeNoiseProfile(
                    byteBuffer, idX, detObj, configParameters, isRangeProfile=True
                )
                finalObj.update(noiseObj)
            elif tlv_type == MMWDEMO_OUTPUT_MSG_NOISE_PROFILE:
                noiseObj = processRangeNoiseProfile(
                    byteBuffer, idX, detObj, configParameters, isRangeProfile=False
                )
                finalObj.update(noiseObj)
            elif tlv_type == MMWDEMO_OUTPUT_MSG_AZIMUT_STATIC_HEAT_MAP:
                heatObj = processAzimuthHeatMap(byteBuffer, idX, configParameters)
                finalObj.update(heatObj)
            elif tlv_type == MMWDEMO_OUTPUT_MSG_RANGE_DOPPLER_HEAT_MAP:
                dopplerObj = processRangeDopplerHeatMap(byteBuffer, idX)
                finalObj.update(dopplerObj)
            elif tlv_type == MMWDEMO_OUTPUT_MSG_STATS:
                statisticsObj = processStatistics(byteBuffer, idX)
                finalObj.update(statisticsObj)

            idX += tlv_length
            # except Error as e:
            #     pass
        # Remove already processed data
        with open(filename, "a") as f:
            writer = csv.DictWriter(f, header)
            writer.writerow(finalObj)
        if 0 < idX < byteBufferLength:
            shiftSize = totalPacketLen

            byteBuffer[: byteBufferLength - shiftSize] = byteBuffer[
                shiftSize:byteBufferLength
            ]
            byteBuffer[byteBufferLength - shiftSize :] = np.zeros(
                len(byteBuffer[byteBufferLength - shiftSize :]), dtype="uint8"
            )
            byteBufferLength = byteBufferLength - shiftSize

            # Check that there are no errors with the buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0
    print(finalObj)
    return dataOK, frameNumber, finalObj


def parseArg():
    parser = argparse.ArgumentParser(description="Change Configuration")
    parser.add_argument(
        "--conf",
        help="Select configuration file",
        default="pointcloud",
        choices=["pointcloud", "macro", "micro"],
    )
    args = parser.parse_args()
    return args


# -------------------------    MAIN   -----------------------------------------

# Configurate the serial port
if __name__ == "__main__":
    args = parseArg()
    configFileName = configs[args.conf]
    CLIport, Dataport = serialConfig(configFileName)
    # Get the configuration parameters from the configuration file
    configParameters = parseConfigFile(configFileName)
    # print(configParameters)

    # Main loop
    detObj = {}
    frameData = {}
    currentIndex = 0
    filename = file_create()

    linecounter = 0

    while True:
        linecounter += 1
        if linecounter > 1000000000:
            linecounter = 0
            filename = file_create()

        try:
            dataOk, frameNumber, finalObj = readAndParseData16xx(
                Dataport, configParameters, filename
            )
            if dataOk:
                # Store the current frame into frameData
                print(finalObj)
                currentIndex += 1

            # time.sleep(0.03)  # Sampling frequency of 30 Hz

        # Stop the program and close everything if Ctrl + c is pressed
        except KeyboardInterrupt:
            CLIport.write("sensorStop\n".encode())
            CLIport.close()
            Dataport.close()
            break
