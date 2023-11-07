import math


class Platform:
    xWR14xx = "xWR14xx"
    xWR16xx = "xWR16xx"
    xWR18xx = "xWR18xx"


class Transform:
    def __init__(self):
        self.Input = {
            "lightSpeed": 300,  # speed of light m/us
            "kB": 1.38064852e-23,  # Bolzmann constant J/K, kgm^2/s^2K
            "cube_4pi": math.pow(4 * math.pi, 3),
            "sdkVersionUint16": 0x0201,  # careful : hex coding or you can express as (major << 8) | (minor)
            "T0_C": 20,  # Ambient temperature, Celcius
            "T0_K": 293.15,  # Ambient temperature, Kelvin
        }

        self.P = {
            "channelCfg": {},
            "adcCfg": {},
            "dataFmt": {},
            "profileCfg": {},
            "chirpCfg": [],
            "frameCfg": {},
            "guiMonitor": {},
            "clutterRemoval": {},
            "lines": [],
        }

    def toLabels(self, nums, p):
        return ", ".join([f"{v:.{p}f}" if p else str(v) for i, v in enumerate(nums)])

    def toCeil(self, x, p):
        return round((x + 0.5) / 10**p, p)

    def toFloor(self, x, p):
        return round((x - 0.5) / 10**p, p)

    def isRR(self):
        return self.Input["subprofile_type"] == "best_range_res"

    def isVR(self):
        return self.Input["subprofile_type"] == "best_vel_res"

    def isBestRange(self):
        return self.Input["subprofile_type"] == "best_range"

    def convertSensitivityLinearTodB(self, linear_value, platform, Num_Virt_Ant):
        if platform == Platform.xWR14xx:
            dB_value = (6 * linear_value) / 512
        else:
            dB_value = (6 * linear_value) / (256 * Num_Virt_Ant)
        return int(dB_value)

    def convertSensitivitydBToLinear(self, dB_value, platform, Num_Virt_Ant):
        if platform == Platform.xWR14xx:
            linear_value = (512 * dB_value) / 6
        else:
            linear_value = (256 * Num_Virt_Ant * dB_value) / 6
        return int(linear_value)

    def setDefaultRangeResConfig(self):
        self.Input["platform"] = Platform.xWR16xx
        self.Input["subprofile_type"] = "best_range_res"
        self.Input["Frequency_band"] = 77
        self.Input["Frame_Rate"] = 10
        self.Input["Azimuth_Resolution"] = "15"  #
        self.Input["Ramp_Slope"] = 70  #
        self.Input["Number_of_chirps"] = 32  #
        self.Input["Num_ADC_Samples"] = 256  #
        self.Input["Maximum_range"] = 9.02
        self.Input["Maximum_radial_velocity"] = 1
        self.Input["Doppler_FFT_size"] = 16  # corresponds to Number_of_chirps = 32

        # hack
        self.Input["RCS_desired"] = 0.5
        self.Input["Doppler_Sensitivity"] = self.convertSensitivityLinearTodB(
            5000, self.Input["platform"], 8
        )  # since azimuth is set to 15 deg, setting virt ant to 8
        if self.Input["platform"] == Platform.xWR14xx:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                1200, self.Input["platform"], 8
            )
        else:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                5000, self.Input["platform"], 8
            )

    def setDefaultVelResConfig(self):
        if "platform" not in self.Input:
            self.Input["platform"] = Platform.xWR16xx
        self.Input["subprofile_type"] = "best_vel_res"
        self.Input["Frequency_band"] = 77
        self.Input["Frame_Rate"] = 10
        self.Input["Azimuth_Resolution"] = "15"
        self.Input["Bandwidth"] = 2
        self.Input["Doppler_FFT_size"] = 128
        self.Input["Num_ADC_Samples"] = 64
        if self.Input["platform"] == Platform.xWR14xx:
            self.Input["Doppler_FFT_size"] = 64
        else:
            self.Input["Doppler_FFT_size"] = 128

        # hack
        self.Input["RCS_desired"] = 0.5
        self.Input["Doppler_Sensitivity"] = self.convertSensitivityLinearTodB(
            5000, self.Input["platform"], 8
        )
        if self.Input["platform"] == Platform.xWR14xx:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                1200, self.Input["platform"], 8
            )
        else:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                5000, self.Input["platform"], 8
            )

    def setDefaultRangeConfig(self):
        if "platform" not in self.Input:
            self.Input["platform"] = Platform.xWR16xx
        self.Input["subprofile_type"] = "best_range"
        self.Input["Frequency_band"] = 77
        self.Input["Frame_Rate"] = 10
        self.Input["Azimuth_Resolution"] = "15"
        self.Input["Maximum_range"] = 50
        self.Input["Number_of_chirps"] = 32  # for 14xx this will end up being 16
        self.Input["Num_ADC_Samples"] = 256
        self.Input["Maximum_radial_velocity"] = 1

        # hack
        self.Input["RCS_desired"] = 0.5
        self.Input["Doppler_Sensitivity"] = self.convertSensitivityLinearTodB(
            5000, self.Input["platform"], 8
        )
        if self.Input["platform"] == Platform.xWR14xx:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                1200, self.Input["platform"], 8
            )
        else:
            self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                5000, self.Input["platform"], 8
            )

    def setSliderRange(self, widget, minVal, maxVal):
        # work around slider bug
        if maxVal < widget.minValue:
            widget.minValue = minVal
            widget.maxValue = maxVal
        else:
            widget.maxValue = maxVal
            widget.minValue = minVal

    def rangeResolutionConstraints1(
        self,
        lightSpeed,
        totalBw,
        rampSlopeLo,
        rampSlopeHi,
        chirpStartTime,
        chirpEndTime,
    ):
        # for RR
        rangeResLo = round(
            lightSpeed
            / (2 * (totalBw - rampSlopeLo * (chirpStartTime + chirpEndTime))),
            3,
        )
        rangeResHi = round(
            lightSpeed
            / (2 * (totalBw - rampSlopeHi * (chirpStartTime + chirpEndTime))),
            3,
        )

        self.setSliderRange(
            templateObj.tiWidgetSliderRangeResolution, rampSlopeLo, rampSlopeHi
        )
        templateObj.tiWidgetSliderRangeResolution.increment = 5
        templateObj.tiWidgetSliderRangeResolution.labels = self.toLabels(
            [
                rangeResLo,
                rangeResHi,
            ]
        )

    def rangeResolutionConstraints2(
        self, lightSpeed, sweepBw, minBandwidth, maxBandwidth
    ):
        # for VR
        # var tmp = round( lightSpeed / ( 2* ( total_bw - ramp_slope * (chirp_start_time + chirp_end_time) ) ), 3);
        rangeResLo = round(lightSpeed / (2 * sweepBw), 3)
        rangeResHi = round(lightSpeed / (2 * sweepBw), 3)

        self.setSliderRange(
            templateObj.tiWidgetSliderRangeResolution, minBandwidth, maxBandwidth
        )
        templateObj.tiWidgetSliderRangeResolution.increment = 0.5
        # templateObj.ti_widget_slider_range_resolution.labels = self.toLabels([range_res_lo, range_res_hi]);
        templateObj.tiWidgetSliderRangeResolution.labels = self.toLabels(
            [
                "coarse",
                "fine",
            ]
        )

    def rangeResolutionConstraints3(self, maximumRange, adcSamplesLo, maxNumAdcSamples):
        # for best range
        rangeResLo = round(maximumRange / (0.8 * maxNumAdcSamples), 3)
        rangeResHi = round(maximumRange / (0.8 * adcSamplesLo), 3)

        if adcSamplesLo == maxNumAdcSamples:
            maxNumAdcSamples = maxNumAdcSamples + 1  # hack

        self.setSliderRange(
            templateObj.tiWidgetSliderRangeResolution, adcSamplesLo, maxNumAdcSamples
        )
        templateObj.tiWidgetSliderRangeResolution.increment = 16
        templateObj.tiWidgetSliderRangeResolution.labels = self.toLabels(
            [
                rangeResHi,
                rangeResLo,
            ]
        )

    def maxRangeConstraints1(self, maxRangeLo, maxRangeHi, inc):
        # for RR, best range
        if maxRangeLo + inc > maxRangeHi:
            maxRangeHi = maxRangeLo

        templateObj.tiWidgetSliderMaxRange.labels = self.toLabels(
            [
                maxRangeLo,
                maxRangeHi,
            ]
        )
        self.setSliderRange(templateObj.tiWidgetSliderMaxRange, maxRangeLo, maxRangeHi)
        templateObj.tiWidgetSliderMaxRange.increment = inc

    def maxRangeConstraints2(
        self, max_range_lo, max_range_hi, adc_samples_lo, max_num_adc_samples
    ):
        # for VR
        # templateObj.ti_widget_slider_max_range.labels = self.toLabels([max_range_lo, max_range_hi]);
        self.setSliderRange(
            templateObj.ti_widget_slider_max_range, adc_samples_lo, max_num_adc_samples
        )
        templateObj.ti_widget_slider_max_range.increment = 16
        templateObj.ti_widget_slider_max_range.labels = self.toLabels(["min", "max"])

    def radialVelocityConstraints1(self, max_radial_vel_lo, max_radial_vel_hi, inc):
        # for RR, best range
        templateObj.ti_widget_slider_max_radial_vel.labels = self.toLabels(
            [max_radial_vel_lo, max_radial_vel_hi]
        )
        self.setSliderRange(
            templateObj.ti_widget_slider_max_radial_vel,
            max_radial_vel_lo,
            max_radial_vel_hi,
        )
        templateObj.ti_widget_slider_max_radial_vel.increment = inc

    def radialVelocityConstraints2(
        self, max_radial_vel_lo, max_radial_vel_hi, N_fft2d_lo, N_fft2d_hi
    ):
        # for VR
        lo = math.log2(N_fft2d_lo)
        hi = math.log2(N_fft2d_hi)
        templateObj.ti_widget_slider_max_radial_vel.labels = self.toLabels(
            [max_radial_vel_lo, max_radial_vel_hi]
        )
        self.setSliderRange(templateObj.ti_widget_slider_max_radial_vel, lo, hi)
        templateObj.ti_widget_slider_max_radial_vel.increment = 1

    def velocityResolutionConstraints1(
        self,
        max_number_of_chirps,
        Number_of_TX,
        N_fft2d_lo,
        Maximum_radial_velocity,
        Doppler_FFT_size,
    ):
        # for RR, best range
        radial_vel_res_values = []
        radial_vel_res_labels = []
        tmp = max_number_of_chirps / Number_of_TX
        while tmp >= N_fft2d_lo:
            radial_vel_res_values.append(tmp)
            radial_vel_res_labels.append(
                self.toCeil(Maximum_radial_velocity / (tmp / 2), 2)
            )
            tmp = tmp >> 1
        templateObj.ti_widget_droplist_radial_vel_resolution.disabled = False
        templateObj.ti_widget_droplist_radial_vel_resolution.values = "|".join(
            str(x) for x in radial_vel_res_values
        )
        templateObj.ti_widget_droplist_radial_vel_resolution.labels = "|".join(
            str(x) for x in radial_vel_res_labels
        )

        # hack
        value = int(
            templateObj.ti_widget_droplist_radial_vel_resolution.selectedValue, 10
        )
        if math.isnan(value) == True:
            value = Doppler_FFT_size
        idx = (
            radial_vel_res_values.index(value) if value in radial_vel_res_values else -1
        )
        if idx >= 0:
            if (
                templateObj.ti_widget_droplist_radial_vel_resolution.selectedValue
                != radial_vel_res_values[idx]
            ):
                templateObj.ti_widget_droplist_radial_vel_resolution.selectedValue = (
                    radial_vel_res_values[idx]
                )
        else:
            templateObj.ti_widget_droplist_radial_vel_resolution.selectedValue = (
                radial_vel_res_values[0] if len(radial_vel_res_values) > 0 else None
            )

    def velocityResolutionConstraints2(self, radial_velocity_resolution):
        # for VR
        templateObj.ti_widget_droplist_radial_vel_resolution.disabled = True
        templateObj.ti_widget_droplist_radial_vel_resolution.labels = str(
            radial_velocity_resolution
        )
        templateObj.ti_widget_droplist_radial_vel_resolution.selectedIndex = 0

    def updateInput(self, changes):
        for k in changes:
            if k in self.Input:
                self.Input[k] = changes[k]

        if self.Input["platform"] == "xWR14xx":
            self.Input["L3_Memory_size"] = 256
            self.Input["CFAR_memory_size"] = 32768  # Bytes
            self.Input["CFAR_window_memory_size"] = 1024  # words - 32-bits
            self.Input["ADCBuf_memory_size"] = 16384
            self.Input["Max_Sampling_Rate"] = 6.25  # room for some round off errors.
            self.Input["Min_Sampling_rate"] = 2  # Msps
            if "Num_Virt_Ant" not in self.Input:
                self.Input["Num_Virt_Ant"] = 8
            if "Range_Sensitivity" not in self.Input:
                self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                    1200, self.Input["platform"], self.Input["Num_Virt_Ant"]
                )
            self.Input["max_number_of_rx"] = 4
            self.Input["max_number_of_tx"] = 3
        elif self.Input["platform"] == "xWR16xx":
            self.Input["L3_Memory_size"] = 640
            self.Input["ADCBuf_memory_size"] = 32768
            self.Input["CFAR_memory_size"] = 0  # Bytes - NA
            self.Input["CFAR_window_memory_size"] = 1024  # words - 32-bits - NA
            self.Input["Max_Sampling_Rate"] = 6.25
            self.Input["Min_Sampling_rate"] = 2  # Msps
            if "Num_Virt_Ant" not in self.Input:
                self.Input["Num_Virt_Ant"] = 8
            if "Range_Sensitivity" not in self.Input:
                self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                    5000, self.Input["platform"], self.Input["Num_Virt_Ant"]
                )
            if "Doppler_Sensitivity" not in self.Input:
                self.Input["Doppler_Sensitivity"] = self.convertSensitivityLinearTodB(
                    5000, self.Input["platform"], self.Input["Num_Virt_Ant"]
                )
            self.Input["max_number_of_rx"] = 4
            self.Input["max_number_of_tx"] = 2
        elif self.Input["platform"] == "xWR18xx":
            self.Input["L3_Memory_size"] = 896
            self.Input["ADCBuf_memory_size"] = 32768
            self.Input["CFAR_memory_size"] = 0  # Bytes - NA
            self.Input["CFAR_window_memory_size"] = 1024  # words - 32-bits - NA
            self.Input["Max_Sampling_Rate"] = 12.5
            self.Input["Min_Sampling_rate"] = 2  # Msps
            if "Num_Virt_Ant" not in self.Input:
                self.Input["Num_Virt_Ant"] = 12
            if "Range_Sensitivity" not in self.Input:
                self.Input["Range_Sensitivity"] = self.convertSensitivityLinearTodB(
                    5000, self.Input["platform"], self.Input["Num_Virt_Ant"]
                )
            if "Doppler_Sensitivity" not in self.Input:
                self.Input["Doppler_Sensitivity"] = self.convertSensitivityLinearTodB(
                    5000, self.Input["platform"], self.Input["Num_Virt_Ant"]
                )
            self.Input["max_number_of_rx"] = 4
            self.Input["max_number_of_tx"] = 3

        if self.Input["Azimuth_Resolution"] == "15 + Elevation":
            if self.Input["platform"] == "Platform.xWR14xx":
                self.Input["Number_of_RX"] = 4
                self.Input["Number_of_TX"] = 3
            elif self.Input["platform"] == "Platform.xWR16xx":
                self.Input["Number_of_RX"] = 4
                self.Input["Number_of_TX"] = 2
            elif self.Input["platform"] == "Platform.xWR18xx":
                self.Input["Number_of_RX"] = 4
                self.Input["Number_of_TX"] = 3
        elif self.Input["Azimuth_Resolution"] == "15":
            self.Input["Number_of_RX"] = 4
            self.Input["Number_of_TX"] = 2
        elif self.Input["Azimuth_Resolution"] == "30":
            self.Input["Number_of_RX"] = 4
            self.Input["Number_of_TX"] = 1
        elif self.Input["Azimuth_Resolution"] == "60":
            self.Input["Number_of_RX"] = 2
            self.Input["Number_of_TX"] = 1
        elif self.Input["Azimuth_Resolution"] == "None (1Rx/1Tx)":
            self.Input["Number_of_RX"] = 1
            self.Input["Number_of_TX"] = 1
        self.Input["Num_Virt_Ant"] = (
            self.Input["Number_of_RX"] * self.Input["Number_of_TX"]
        )
        self.Input["ADC_bits"] = 16
        self.Input["ADC_samples_type"] = 2
        self.Input["Bandwidth_list"] = [0.5, 1, 1, 5, 2, 2.5, 3, 3.5, 4]
        self.Input["Min_Allowable_Bandwidth"] = 0.5
        self.Input["Chirp_end_guard_time"] = 1
        if (
            self.Input["platform"] == "Platform.xWR16xx"
            and self.Input["sdkVersionUint16"] >= 0x0101
        ):
            self.Input["chirps_per_interrupt"] = 0
        else:
            self.Input["chirps_per_interrupt"] = 1
        self.Input["Chirp_Start_Time"] = 7
        self.Input["Min_Interchirp_dur"] = 7
        self.Input["Doppler_FFT_list"] = [16, 32, 64, 128, 256]
        N_fft2d_lo = self.Input["Doppler_FFT_list"][0]
        adc_samples_lo = 64
        self.Input["Max_Slope"] = 100
        self.Input["Maximum_range_list"] = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        self.Input["Gr"] = 8
        self.Input["Gt"] = 8
        self.Input["Ld"] = 2
        self.Input["Lim"] = 2
        if self.Input["Num_Virt_Ant"] == 12:
            self.Input["Lncoh"] = 3
        elif self.Input["Num_Virt_Ant"] == 8:
            self.Input["Lncoh"] = 2.2
        elif self.Input["Num_Virt_Ant"] == 4:
            self.Input["Lncoh"] = 1.5
        elif self.Input["Num_Virt_Ant"] == 2:
            self.Input["Lncoh"] = 0.7
        elif self.Input["Num_Virt_Ant"] == 2:
            self.Input["Lncoh"] = 0
        else:
            self.Input["Lncoh"] = 6

        self.Input["Ls"] = 1
        self.Input["NF"] = 16 if self.Input["Frequency_band"] == 77 else 15
        self.Input["Pt"] = 12
        self.Input["SNR_det"] = 12
        self.Input["loss_dB"] = (
            self.Input["Pt"]
            + self.Input["Gt"]
            + self.Input["Gr"]
            - self.Input["Lncoh"]
            - self.Input["Ld"]
            - self.Input["Ls"]
            - self.Input["Lim"]
            - self.Input["SNR_det"]
            - self.Input["NF"]
        )
        self.Input["loss_linear"] = pow(10, self.Input["loss_dB"] / 10)

        self.Input["Max_Allowable_Bandwidth"] = (
            4 if self.Input["Frequency_band"] == 77 else 1
        )  # GHz
        self.Input["Total_BW"] = None
        tmp = self.isRR()
        if self.Input["subprofile_type"] == "best_range_res":
            if self.Input["Frequency_band"] == 77:
                self.Input["Bandwidth"] = 4
            elif self.Input["Frequency_band"] == 76:
                self.Input["Bandwidth"] = 1
            self.Input["Total_BW"] = self.Input["Bandwidth"] * 1000
            self.Input["min_Ramp_Slope"] = 20
            if self.Input["platform"] == Platform.xWR14xx:
                self.Input["min_Ramp_Slope"] = 35  # max ADC samples is 256
            if not self.Input["Ramp_Slope"]:
                self.Input["Ramp_Slope"] = self.Input["min_Ramp_Slope"]  # preset
            if not self.Input["Number_of_chirps"]:
                self.Input["Number_of_chirps"] = 16  # preset
            self.Input["Max_Slope"] = min(
                self.Input["Max_Slope"],
                math.floor(
                    (
                        self.Input["Max_Allowable_Bandwidth"]
                        * 1000
                        * self.Input["Max_Sampling_Rate"]
                    )
                    / (
                        adc_samples_lo
                        + self.Input["Max_Sampling_Rate"]
                        * (
                            self.Input["Chirp_Start_Time"]
                            + self.Input["Chirp_end_guard_time"]
                        )
                    )
                ),
            )
            self.Input["Max_Slope"] = math.floor(self.Input["Max_Slope"] / 5) * 5
            self.rangeResolutionConstraints1(
                self.Input["lightSpeed"],
                self.Input["Total_BW"],
                self.Input["min_Ramp_Slope"],
                self.Input["Max_Slope"],
                self.Input["Chirp_Start_Time"],
                self.Input["Chirp_end_guard_time"],
            )
        elif self.Input["subprofile_type"] == "best_vel_res":
            if not self.Input["Bandwidth"]:
                self.Input["Bandwidth"] = 0.5  # preset
            if not self.Input["Num_ADC_Samples"]:
                self.Input["Num_ADC_Samples"] = adc_samples_lo
            if not self.Input["Doppler_FFT_size"]:
                self.Input["Doppler_FFT_size"] = N_fft2d_lo
            self.Input["Total_BW"] = self.Input["Bandwidth"] * 1000
        elif self.Input["subprofile_type"] == "best_range":
            if not self.Input["Number_of_chirps"]:
                self.Input["Number_of_chirps"] = 16  # preset
        self.Input["Frame_duration"] = round(1000 / self.Input["Frame_Rate"], 3)
        max_Ramp_Slope1 = int(
            self.Input["Bandwidth"]
            * 1000
            / (
                32 / self.Input["Max_Sampling_Rate"]
                + self.Input["Chirp_Start_Time"]
                + self.Input["Chirp_end_guard_time"]
            )
        )
        self.Input["max_Ramp_Slope"] = max(
            min(self.Input["Max_Slope"], max_Ramp_Slope1), 5
        )

        if self.Input["subprofile_type"] == "best_vel_res":
            self.Input["Radial_velocity_Resolution"] = self.toCeil(
                self.Input["lightSpeed"]
                / (self.Input["Frequency_band"] * self.Input["Frame_duration"]),
                2,
            )
            self.Input["Maximum_radial_velocity"] = round(
                (
                    self.Input["Radial_velocity_Resolution"]
                    * self.Input["Doppler_FFT_size"]
                )
                / 2,
                2,
            )
            self.Input["Number_of_chirps"] = (
                self.Input["Doppler_FFT_size"] * self.Input["Number_of_TX"]
            )
            min_Ramp_Slope = min(
                round(
                    self.Input["Bandwidth"]
                    * 1000
                    / (
                        (self.Input["Frame_duration"] * 1000)
                        / (2 * self.Input["Number_of_chirps"])
                        - self.Input["Min_Interchirp_dur"]
                    ),
                    3,
                ),
                self.Input["max_Ramp_Slope"],
            )
            self.Input["Ramp_Slope"] = max(
                min(
                    round(
                        self.Input["Bandwidth"]
                        * 1000
                        / (
                            self.Input["Chirp_end_guard_time"]
                            + self.Input["Chirp_Start_Time"]
                            + self.Input["Num_ADC_Samples"]
                            / self.Input["Max_Sampling_Rate"]
                        ),
                        3,
                    ),
                    self.Input["Max_Slope"],
                ),
                min_Ramp_Slope,
            )
        elif self.Input["subprofile_type"] == "best_range":
            self.Input["Range_Resolution"] = round(
                self.Input["Maximum_range"] / (0.8 * self.Input["Num_ADC_Samples"]), 3
            )
            self.Input["Sweep_BW"] = round(
                self.Input["lightSpeed"] / (2 * self.Input["Range_Resolution"]), 3
            )
            ramp_slope1 = round(
                (self.Input["lightSpeed"] * 0.8 * self.Input["Max_Sampling_Rate"])
                / (2 * self.Input["Maximum_range"]),
                3,
            )
            ramp_slope2 = self.toCeil(
                (
                    self.Input["Max_Allowable_Bandwidth"] * 1000
                    - (self.Input["lightSpeed"] * 0.8 * self.Input["Num_ADC_Samples"])
                    / (2 * self.Input["Maximum_range"])
                )
                / (self.Input["Chirp_Start_Time"] + self.Input["Chirp_end_guard_time"]),
                3,
            )
            if ramp_slope2 <= 0:
                ramp_slope2 = ramp_slope1
            self.Input["Ramp_Slope"] = min(
                ramp_slope1, ramp_slope2, self.Input["Max_Slope"]
            )

        if self.Input["subprofile_type"] != "best_range":
            self.Input["Chirp_duration"] = round(
                self.Input["Total_BW"] / self.Input["Ramp_Slope"], 2
            )
            self.Input["ADC_Collection_Time"] = round(
                self.Input["Chirp_duration"]
                - self.Input["Chirp_Start_Time"]
                - self.Input["Chirp_end_guard_time"],
                2,
            )
            self.Input["Sweep_BW"] = round(
                self.Input["ADC_Collection_Time"] * self.Input["Ramp_Slope"], 3
            )
            self.Input["Range_Resolution"] = round(
                self.Input["lightSpeed"] / (2 * self.Input["Sweep_BW"]), 3
            )
            self.Input["ADC_Sampling_Rate"] = self.toFloor(
                (self.Input["Ramp_Slope"] * self.Input["Num_ADC_Samples"])
                / self.Input["Sweep_BW"],
                3,
            )
            self.Input["Range_FFT_size"] = 1 << math.ceil(
                math.log2(self.Input["Num_ADC_Samples"])
            )  # TODO hack see below  # MMWSDK-580
        else:
            self.Input["ADC_Collection_Time"] = round(
                self.Input["Sweep_BW"] / self.Input["Ramp_Slope"], 2
            )
            self.Input["Chirp_duration"] = round(
                self.Input["ADC_Collection_Time"]
                + self.Input["Chirp_end_guard_time"]
                + self.Input["Chirp_Start_Time"],
                2,
            )
            self.Input["ADC_Sampling_Rate"] = self.toFloor(
                (2 * self.Input["Ramp_Slope"] * self.Input["Maximum_range"])
                / (self.Input["lightSpeed"] * 0.8),
                3,
            )
            self.Input["Total_BW"] = (
                self.Input["Chirp_duration"] * self.Input["Ramp_Slope"]
            )
            self.Input["Range_FFT_size"] = 1 << math.ceil(
                math.log2(self.Input["Num_ADC_Samples"])
            )  # TODO hack see below

        if self.Input["subprofile_type"] != "best_vel_res":
            self.Input["Doppler_FFT_size"] = (
                self.Input["Number_of_chirps"] / self.Input["Number_of_TX"]
            )
        # self.Input["Doppler_FFT_size"] = from max radial velocity selection  # VR Sheet

        self.Input["frame_rate_max"] = 1000000 / (
            (
                self.Input["Total_BW"] / self.Input["Ramp_Slope"]
                + self.Input["Min_Interchirp_dur"]
            )
            * self.Input["Doppler_FFT_size"]
            * self.Input["Number_of_TX"]
            * 2
        )
        self.Input["frame_rate_min"] = 1

        if self.Input["subprofile_type"] != "best_vel_res":
            self.Input["Inter_chirp_duration"] = math.floor(
                (self.Input["lightSpeed"] * 1000)
                / (
                    4
                    * self.Input["Frequency_band"]
                    * self.Input["Maximum_radial_velocity"]
                    * self.Input["Number_of_TX"]
                )
                - self.Input["Chirp_duration"]
            )
        else:
            self.Input["Inter_chirp_duration"] = math.floor(
                (self.Input["Frame_duration"] / 2 / self.Input["Number_of_chirps"])
                * 1000
                - self.Input["Chirp_duration"]
            )  # VR sheet

        self.Input["Frame_time_active"] = (
            (self.Input["Chirp_duration"] + self.Input["Inter_chirp_duration"])
            * self.Input["Number_of_chirps"]
            / 1000
        )

        max_Bandwidth1 = (
            self.Input["Max_Slope"]
            * (
                (self.Input["Frame_duration"] * 1000)
                / (2 * self.Input["Number_of_TX"] * self.Input["Doppler_FFT_size"])
                - self.Input["Min_Interchirp_dur"]
            )
        ) / 1000
        max_Bandwidth2 = (
            math.floor(
                (
                    self.Input["lightSpeed"]
                    / (
                        self.Input["Maximum_radial_velocity"]
                        * self.Input["Frame_duration"]
                    )
                    + (
                        self.Input["Max_Slope"]
                        * (
                            self.Input["Chirp_end_guard_time"]
                            + self.Input["Chirp_Start_Time"]
                        )
                    )
                    / 1000
                )
                / 0.5
            )
            * 0.5
        )
        self.Input["max_Bandwidth"] = min(
            [self.Input["Max_Allowable_Bandwidth"], max_Bandwidth1, max_Bandwidth2]
        )
        self.Input["max_Inter_chirp_dur"] = 5242.87
        max_inter_chirp_duration1 = (
            self.Input["Frame_duration"] / 2 / self.Input["Number_of_chirps"]
        ) * 1000 - self.Input["Chirp_duration"]
        idleTime_hi = 5242.87
        self.Input["max_inter_chirp_duration"] = self.toFloor(
            min(max_inter_chirp_duration1, idleTime_hi), 2
        )
        N_fft1d_max1 = None
        adc_samples_lo_calc = adc_samples_lo
        N_fft1d_max2 = 1 << math.floor(
            math.log2(
                (self.Input["L3_Memory_size"] * 1024)
                / (4 * self.Input["Number_of_RX"] * self.Input["Number_of_TX"] + 2)
                / N_fft2d_lo
            )
        )  # RR,best range
        N_fft1d_max4 = 4096  # junk - big value
        N_fft1d_max5 = 4096  # junk - big value
        N_fft1d_max6 = 4096  # junk - big value
        if self.Input["platform"] == Platform.xWR14xx:
            N_fft1d_max4 = 1 << math.floor(
                math.log2(self.Input["CFAR_memory_size"] / (2 * N_fft2d_lo))
            )
            N_fft1d_max6 = (
                self.Input["CFAR_window_memory_size"] - N_fft2d_lo
            )  # MMWSDK-578

        if self.Input["subprofile_type"] == "best_range_res":
            N_fft1d_max1 = (
                self.Input["Max_Sampling_Rate"] * self.Input["Sweep_BW"]
            ) / self.Input["Ramp_Slope"]
            adc_samples_lo_calc = max(
                adc_samples_lo,
                math.ceil(
                    (self.Input["Sweep_BW"] * self.Input["Min_Sampling_rate"])
                    / self.Input["Ramp_Slope"]
                ),
            )
            adc_samples_lo_calc = 16 * math.ceil(adc_samples_lo_calc / 16)  # MMWSDK-587
        elif self.Input["subprofile_type"] == "best_vel_res":
            N_fft1d_max1 = (
                (self.Input["Frame_duration"] * 1000)
                / (2 * self.Input["Number_of_TX"] * self.Input["Doppler_FFT_size"])
                - self.Input["Min_Interchirp_dur"]
                - self.Input["Chirp_end_guard_time"]
                - self.Input["Chirp_Start_Time"]
            ) * self.Input[
                "Max_Sampling_Rate"
            ]  # VR sheet
            N_fft1d_max2 = 1 << math.floor(
                math.log2(
                    (self.Input["L3_Memory_size"] * 1024)
                    / (4 * self.Input["Number_of_RX"] + 2 / self.Input["Number_of_TX"])
                    / self.Input["Number_of_chirps"]
                )
            )  # VR sheet
            if self.Input["platform"] == Platform.xWR14xx:
                N_fft1d_max4 = 1 << math.floor(
                    math.log2(
                        (self.Input["CFAR_memory_size"] * self.Input["Number_of_TX"])
                        / (2 * self.Input["Number_of_chirps"])
                    )
                )
                N_fft1d_max6 = (
                    self.Input["CFAR_window_memory_size"]
                    - self.Input["Number_of_chirps"] / self.Input["Number_of_TX"]
                )  # MMWSDK-578
            N_fft1d_max5 = (
                math.floor(50 / (0.8 * self.Input["Range_Resolution"]) * 100) / 100
            )
        elif self.Input["subprofile_type"] == "best_range":
            N_fft1d_max1 = (
                (
                    self.Input["Max_Allowable_Bandwidth"] * 1000
                    - self.Input["Ramp_Slope"]
                    * (
                        self.Input["Chirp_end_guard_time"]
                        + self.Input["Chirp_Start_Time"]
                    )
                )
                * self.Input["ADC_Sampling_Rate"]
            ) / self.Input[
                "Ramp_Slope"
            ]  # Range Sheet
        N_fft1d_max1 = math.floor(N_fft1d_max1)

        # if chirps per interrupt is set to max allowed, then for limits compute purposes,
        # need to use 1, else what is intended by user.
        if self.Input["chirps_per_interrupt"] == 0:
            chirpsPerInt = 1
        else:
            chirpsPerInt = self.Input["chirps_per_interrupt"]
        N_fft1d_max3 = int(
            self.Input["ADCBuf_memory_size"]
            / (
                (
                    (self.Input["Number_of_RX"] * chirpsPerInt * self.Input["ADC_bits"])
                    / 8
                )
                * self.Input["ADC_samples_type"]
            )
        )

        self.Input["max_num_adc_samples"] = min(
            [
                N_fft1d_max1,
                N_fft1d_max2,
                N_fft1d_max3,
                N_fft1d_max4,
                N_fft1d_max5,
                N_fft1d_max6,
            ]
        )
        self.Input["max_num_adc_samples"] = max(
            [
                self.Input["max_num_adc_samples"],
                adc_samples_lo_calc,
            ]
        )

        if self.Input["subprofile_type"] == "best_vel_res":
            max2 = int(
                (self.Input["L3_Memory_size"] * 1024)
                / (4 * self.Input["Number_of_RX"] + 2 / self.Input["Number_of_TX"])
                / adc_samples_lo
            )
            max3 = int(
                ((self.Input["Frame_duration"] / 2) * 1000)
                / (
                    self.Input["Min_Interchirp_dur"]
                    + self.Input["Chirp_Start_Time"]
                    + self.Input["Chirp_end_guard_time"]
                    + adc_samples_lo / self.Input["Max_Sampling_Rate"]
                )
            )
            max4 = 4096  # junk - large value
            max5 = 4096  # junk - large value
            if self.Input["platform"] == Platform.xWR14xx:
                max4 = int(
                    (self.Input["CFAR_memory_size"] * self.Input["Number_of_TX"])
                    / (2 * adc_samples_lo)
                )
                max5 = int(
                    (self.Input["CFAR_window_memory_size"] - adc_samples_lo)
                    * self.Input["Number_of_TX"]
                )
            max6 = 255 * self.Input["Number_of_TX"]  # RF front end requirement
            self.Input["max_number_of_chirps"] = (
                1
                << int(
                    math.log2(
                        min([max2, max3, max4, max5, max6]) / self.Input["Number_of_TX"]
                    )
                )
            ) * self.Input["Number_of_TX"]
        else:
            chirp_limits = []
            chirp_limits.append(
                ((2 * self.Input["Frequency_band"]) / (self.Input["Sweep_BW"] / 1000))
                * self.Input["Number_of_TX"]
            )  # RR,range,
            chirp_limits.append(
                (self.Input["L3_Memory_size"] * 1024)
                / (4 * self.Input["Number_of_RX"] + 2 / self.Input["Number_of_TX"])
                / self.Input["Range_FFT_size"]
            )  # RR,range
            if self.Input["platform"] == Platform.xWR14xx:
                chirp_limits.append(
                    (self.Input["CFAR_memory_size"] * self.Input["Number_of_TX"])
                    / (2 * self.Input["Range_FFT_size"])
                )  # RR,range
                chirp_limits.append(
                    (
                        self.Input["CFAR_window_memory_size"]
                        - self.Input["Range_FFT_size"]
                    )
                    * self.Input["Number_of_TX"]
                )  # RR,range
            chirp_limits.append(
                255 * self.Input["Number_of_TX"]
            )  # Rf front end requirement
            if self.Input["subprofile_type"] == "best_range":
                chirp_limits.append(
                    (self.Input["Frame_duration"] * 1000)
                    / 2
                    / (
                        self.Input["Inter_chirp_duration"]
                        + self.Input["Chirp_duration"]
                    )
                )  # range
            self.Input["max_number_of_chirps"] = (
                1
                << math.floor(math.log2(min(chirp_limits) / self.Input["Number_of_TX"]))
            ) * self.Input["Number_of_TX"]

        # Input.Maximum_radial_velocity; # directly from widget for RR, best range
        # Input.Maximum_range; # directly from widget for RR, best range
        if self.Input["subprofile_type"] == "best_vel_res":
            self.Input["Maximum_range"] = self.toFloor(
                0.8 * self.Input["Range_Resolution"] * self.Input["Num_ADC_Samples"], 2
            )  # VR sheet # Winnie's bug : Note Math.floor() only takes 1 arg. Use self.toFloor(n, p)

        self.Input["min_Bandwidth"] = self.Input["Min_Allowable_Bandwidth"]

        if self.Input["subprofile_type"] == "best_range_res":
            # best range: range resolution widget selects num adc samples directly
            # VR: max range widget selects num add samples directly
            # [ hack
            if self.Input["Num_ADC_Samples"] and not self.Input["Maximum_range"]:
                # logic came here since Max Range value is out of bounds for min/max set in previous call.
                # so num ADC samples cannot be trusted as well.
                if (
                    self.Input["Num_ADC_Samples"] < adc_samples_lo_calc
                    or self.Input["Num_ADC_Samples"] > self.Input["max_num_adc_samples"]
                ):
                    self.Input["Num_ADC_Samples"] = adc_samples_lo_calc
                self.Input["Maximum_range"] = self.toFloor(
                    0.8
                    * self.Input["Range_Resolution"]
                    * self.Input["Num_ADC_Samples"],
                    2,
                )
            else:
                # ]
                self.Input["Num_ADC_Samples"] = 16 * math.floor(
                    self.Input["Maximum_range"]
                    / (0.8 * self.Input["Range_Resolution"] * 16)
                )  # but range sheet: range resolution widget selects num adc samples directly
            self.Input["ADC_Sampling_Rate"] = self.toFloor(
                self.Input["Ramp_Slope"]
                * self.Input["Num_ADC_Samples"]
                / self.Input["Sweep_BW"],
                3,
            )  # RR,VR
            self.Input["Range_FFT_size"] = 1 << math.ceil(
                math.log2(self.Input["Num_ADC_Samples"])
            )

        self.Input["Non_sweep_BW"] = (
            self.Input["Chirp_Start_Time"] + self.Input["Chirp_end_guard_time"]
        ) * self.Input["Ramp_Slope"]

        # self.Input.Range_FFT_size = 1<<Math.ceil(Math.log2(self.Input.ADC_Sampling_Rate*self.Input.ADC_Collection_Time)); // TODO hack move up a bit

        if self.Input["subprofile_type"] != "best_range":
            self.Input["Sweep_BW"] = (
                self.Input["ADC_Collection_Time"] * self.Input["Ramp_Slope"]
            )
            self.Input["Range_Resolution"] = round(
                self.Input["lightSpeed"] / (2 * self.Input["Sweep_BW"]), 3
            )
        else:
            self.Input["Range_Resolution"] = round(
                self.Input["Maximum_range"] / (0.8 * self.Input["Num_ADC_Samples"]), 3
            )  # Range Sheet
            self.Input["Sweep_BW"] = round(
                self.Input["lightSpeed"] / (2 * self.Input["Range_Resolution"]), 3
            )  # Range Sheet

        self.Input["Range_high"] = self.toFloor(
            0.8 * self.Input["Range_Resolution"] * self.Input["max_num_adc_samples"], 2
        )
        self.Input["Range_low"] = self.toCeil(
            0.8 * self.Input["Range_Resolution"] * adc_samples_lo_calc, 2
        )

        RangeIncrements = 0.01
        if self.Input["subprofile_type"] == "best_range_res":
            if self.Input["platform"] in [Platform.xWR16xx, Platform.xWR18xx]:
                # "16" is due to the limitation on ADC samples in the demo
                RangeIncrements = self.toCeil(
                    0.8 * self.Input["Range_Resolution"] * 16, 2
                )
            self.maxRangeConstraints1(
                self.Input["Range_low"], self.Input["Range_high"], RangeIncrements
            )
        elif self.Input["subprofile_type"] == "best_vel_res":
            self.rangeResolutionConstraints2(
                self.Input["lightSpeed"],
                self.Input["Sweep_BW"],
                self.Input["min_Bandwidth"],
                self.Input["max_Bandwidth"],
            )
            self.maxRangeConstraints2(
                self.Input["Range_low"],
                self.Input["Range_high"],
                adc_samples_lo,
                self.Input["max_num_adc_samples"],
            )
            pass
        elif self.Input["subprofile_type"] == "best_range":
            lo = self.Input["Maximum_range_list"][0]
            if self.Input["Frequency_band"] == 76:
                lo = self.Input["Maximum_range_list"][
                    1
                ]  # (c*0.8*adc_samples_lo/1Ghz)/2 = 7.68 //MMWSDK-590
            hi = self.Input["Maximum_range_list"][-1]
            inc = (
                self.Input["Maximum_range_list"][1]
                - self.Input["Maximum_range_list"][0]
            )
            self.maxRangeConstraints1(lo, hi, inc)
            self.rangeResolutionConstraints3(
                self.Input["Maximum_range"],
                adc_samples_lo,
                self.Input["max_num_adc_samples"],
            )

        self.Input["Wavelength"] = (
            self.Input["lightSpeed"] / self.Input["Frequency_band"]
        )

        # self.Input['Range_Sensitivity'] = 5000
        self.Input["RCS_des_max"] = self.Input["RCS_Rmax"]
        # self.Input['RCS_desired']
        max_range_exp_4 = self.Input["Maximum_range"] ** 4
        wavelength_exp_2 = self.Input["Wavelength"] ** 2
        self.Input["RCS_Rmax"] = round(
            (
                0.8
                * max_range_exp_4
                * self.Input["cube_4pi"]
                * self.Input["kB"]
                * self.Input["T0_K"]
                * 1000000
                * 1000000
            )
            / (
                0.001
                * self.Input["loss_linear"]
                * wavelength_exp_2
                * self.Input["Number_of_RX"]
                * self.Input["Chirp_duration"]
                * self.Input["Number_of_chirps"]
            ),
            6,
        )
        self.Input["Rmax_RCS_desired"] = round(
            (
                (
                    0.001
                    * self.Input["RCS_desired"]
                    * self.Input["loss_linear"]
                    * wavelength_exp_2
                    * self.Input["Number_of_RX"]
                    * self.Input["Chirp_duration"]
                    * self.Input["Number_of_chirps"]
                )
                / (
                    0.8
                    * self.Input["cube_4pi"]
                    * self.Input["kB"]
                    * self.Input["T0_K"]
                    * 1000000
                    * 1000000
                )
            )
            ** (1 / 4),
            3,
        )

        self.Input["Single_chirp_time"] = round(
            self.Input["Total_BW"] + self.Input["Inter_chirp_duration"], 2
        )

        if self.Input["subprofile_type"] != "best_vel_res":
            self.Input["v_max_high"] = self.toFloor(
                (self.Input["lightSpeed"] * 1000)
                / (
                    4
                    * self.Input["Frequency_band"]
                    * (self.Input["Chirp_duration"] + self.Input["Min_Interchirp_dur"])
                    * self.Input["Number_of_TX"]
                ),
                2,
            )
            self.Input["v_max_low"] = self.toCeil(
                (self.Input["lightSpeed"] * 1000)
                / (
                    4
                    * self.Input["Frequency_band"]
                    * (
                        self.Input["Chirp_duration"]
                        + self.Input["max_inter_chirp_duration"]
                    )
                    * self.Input["Number_of_TX"]
                ),
                2,
            )
        else:
            self.Input["v_max_high"] = (
                self.Input["Radial_velocity_Resolution"]
                * self.Input["max_number_of_chirps"]
            ) / (
                2 * self.Input["Number_of_TX"]
            )  # VR sheet
            self.Input["v_max_low"] = (
                self.Input["Radial_velocity_Resolution"] * N_fft2d_lo
            ) / 2  # VR sheet

        if (
            self.Input["subprofile_type"] == "best_range_res"
            or self.Input["subprofile_type"] == "best_range"
        ):
            self.radialVelocityConstraints1(
                self.Input["v_max_low"], self.Input["v_max_high"], 0.01
            )  # RR, best range
        else:
            self.radialVelocityConstraints2(
                self.Input["v_max_low"],
                self.Input["v_max_high"],
                N_fft2d_lo,
                self.Input["max_number_of_chirps"] / self.Input["Number_of_TX"],
            )

        self.Input["vel_res_high"] = self.toCeil(
            (self.Input["Maximum_radial_velocity"] * 2) / N_fft2d_lo, 2
        )
        self.Input["vel_res_low"] = self.toCeil(
            (self.Input["Maximum_radial_velocity"] * 2 * self.Input["Number_of_TX"])
            / self.Input["max_number_of_chirps"],
            2,
        )

        if (
            self.Input["subprofile_type"] == "best_range_res"
            or self.Input["subprofile_type"] == "best_range"
        ):
            self.velocityResolutionConstraints1(
                self.Input["max_number_of_chirps"],
                self.Input["Number_of_TX"],
                N_fft2d_lo,
                self.Input["Maximum_radial_velocity"],
                self.Input["Doppler_FFT_size"],
            )  # RR, best range
        valueN2d = int(
            templateObj.ti_widget_droplist_radial_vel_resolution.selectedValue
        )
        if not math.isnan(valueN2d):
            self.Input["N_fft2d"] = valueN2d
        if self.Input["N_fft2d"]:
            # RR, best range
            # radial velocity resolution derived values
            self.Input["Doppler_FFT_size"] = self.Input["N_fft2d"]
            self.Input["Number_of_chirps"] = (
                self.Input["N_fft2d"] * self.Input["Number_of_TX"]
            )
            self.Input["Radial_velocity_Resolution"] = self.toCeil(
                self.Input["Maximum_radial_velocity"] / (self.Input["N_fft2d"] / 2), 2
            )
        elif self.Input["subprofile_type"] == "best_vel_res":
            # radial_velocity_resolution
            self.velocityResolutionConstraints2(
                self.Input["Radial_velocity_Resolution"]
            )

    # TODO?
    # self.brief() # We need to update the labels after this

    def getVersionString(self, ver_uint16):
        hex_str = hex(ver_uint16)[2:]  # convert to hex and remove prefix "0x"
        hex_str = hex_str.rjust(4, "0")  # make width=4 by adding leading zeros
        hex_str = hex_str[:2] + "." + hex_str[2:]  # separate into major/minor
        return hex_str

    def generate_ChannelCfg(self):
        if self.Input["Number_of_RX"] == 4:
            self.P["channelCfg"]["rxChannelEn"] = 15
        elif self.Input["Number_of_RX"] == 3:
            self.P["channelCfg"]["rxChannelEn"] = 7
        elif self.Input["Number_of_RX"] == 2:
            self.P["channelCfg"]["rxChannelEn"] = 3
        elif self.Input["Number_of_RX"] == 1:
            self.P["channelCfg"]["rxChannelEn"] = 2
        else:
            self.P["channelCfg"]["rxChannelEn"] = 0

        if (
            self.Input["platform"] == Platform.xWR14xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            if self.Input["Number_of_TX"] == 3:
                self.P["channelCfg"]["txChannelEn"] = 7
            elif self.Input["Number_of_TX"] == 2:
                self.P["channelCfg"]["txChannelEn"] = 5
            elif self.Input["Number_of_TX"] == 1:
                self.P["channelCfg"]["txChannelEn"] = 1
            else:
                self.P["channelCfg"]["txChannelEn"] = 0
        elif self.Input["platform"] == Platform.xWR16xx:
            if self.Input["Number_of_TX"] == 2:
                self.P["channelCfg"]["txChannelEn"] = 3
            elif self.Input["Number_of_TX"] == 1:
                self.P["channelCfg"]["txChannelEn"] = 1
            else:
                self.P["channelCfg"]["txChannelEn"] = 0
        else:
            self.P["channelCfg"]["txChannelEn"] = 0

        self.P["channelCfg"]["cascading"] = 0
        self.P["lines"].append(
            "channelCfg {} {} {}".format(
                self.P["channelCfg"]["rxChannelEn"],
                self.P["channelCfg"]["txChannelEn"],
                self.P["channelCfg"]["cascading"],
            )
        )

    def generate_adcCfg(self):
        self.P["adcCfg"]["numADCBits"] = 2 if self.Input["ADC_bits"] == 16 else "NA"
        self.P["adcCfg"]["adcOutputFmt"] = (
            1 if self.Input["ADC_samples_type"] == 2 else 0
        )
        self.P["adcCfg"]["justification"] = 0  # TODO remove
        self.P["lines"].append(
            "adcCfg "
            + str(self.P["adcCfg"]["numADCBits"])
            + " "
            + str(self.P["adcCfg"]["adcOutputFmt"])
        )

    def generate_adcbufCfg(self):
        self.P["dataFmt"]["rxChannelEn"] = self.P["channelCfg"]["rxChannelEn"]
        self.P["dataFmt"]["adcOutputFmt"] = (
            0 if self.Input["ADC_samples_type"] == 2 else 1
        )
        if self.Input["platform"] in [Platform.xWR16xx, Platform.xWR18xx]:
            self.P["dataFmt"]["SampleSwap"] = 0
            self.P["dataFmt"]["ChanInterleave"] = 1
        else:
            self.P["dataFmt"]["SampleSwap"] = 1
            self.P["dataFmt"]["ChanInterleave"] = 0
        self.P["dataFmt"]["chirpThreshold"] = self.Input["chirps_per_interrupt"]
        if (self.Input["platform"] in [Platform.xWR16xx, Platform.xWR18xx]) and (
            self.Input["sdkVersionUint16"] >= 0x0101
        ):
            self.P["lines"].append(
                "adcbufCfg -1 "
                + " ".join(
                    str(x)
                    for x in [
                        self.P["dataFmt"]["adcOutputFmt"],
                        self.P["dataFmt"]["SampleSwap"],
                        self.P["dataFmt"]["ChanInterleave"],
                        self.P["dataFmt"]["chirpThreshold"],
                    ]
                )
            )
        else:
            self.P["lines"].append(
                "adcbufCfg "
                + " ".join(
                    str(x)
                    for x in [
                        self.P["dataFmt"]["adcOutputFmt"],
                        self.P["dataFmt"]["SampleSwap"],
                        self.P["dataFmt"]["ChanInterleave"],
                        self.P["dataFmt"]["chirpThreshold"],
                    ]
                )
            )

    def generate_profileCfg(self):
        self.P["profileCfg"]["profileId"] = 0
        self.P["profileCfg"]["startFreq"] = self.Input["Frequency_band"]
        self.P["profileCfg"]["idleTime"] = self.Input["Inter_chirp_duration"]
        self.P["profileCfg"]["adcStartTime"] = self.Input["Chirp_Start_Time"]
        self.P["profileCfg"]["rampEndTime"] = self.Input["Chirp_duration"]
        self.P["profileCfg"]["txOutPower"] = 0
        self.P["profileCfg"]["txPhaseShifter"] = 0
        self.P["profileCfg"]["freqSlopeConst"] = self.Input["Ramp_Slope"]
        self.P["profileCfg"]["txStartTime"] = 1
        self.P["profileCfg"]["numAdcSamples"] = self.Input["Num_ADC_Samples"]
        self.P["profileCfg"]["digOutSampleRate"] = (
            self.Input["ADC_Sampling_Rate"] * 1000
        )
        self.P["profileCfg"]["hpfCornerFreq1"] = 0
        self.P["profileCfg"]["hpfCornerFreq2"] = 0
        self.P["profileCfg"]["rxGain"] = 30

        self.P["lines"].append(
            " ".join(
                [
                    "profileCfg",
                    str(self.P["profileCfg"]["profileId"]),
                    str(self.P["profileCfg"]["startFreq"]),
                    str(self.P["profileCfg"]["idleTime"]),
                    str(self.P["profileCfg"]["adcStartTime"]),
                    str(self.P["profileCfg"]["rampEndTime"]),
                    str(self.P["profileCfg"]["txOutPower"]),
                    str(self.P["profileCfg"]["txPhaseShifter"]),
                    str(self.P["profileCfg"]["freqSlopeConst"]),
                    str(self.P["profileCfg"]["txStartTime"]),
                    str(self.P["profileCfg"]["numAdcSamples"]),
                    str(self.P["profileCfg"]["digOutSampleRate"]),
                    str(self.P["profileCfg"]["hpfCornerFreq1"]),
                    str(self.P["profileCfg"]["hpfCornerFreq2"]),
                    str(self.P["profileCfg"]["rxGain"]),
                ]
            )
        )

    def generate_chirpCfg(self):
        chirpCfg = {}
        self.P["chirpCfg"].append(chirpCfg)
        chirpCfg["startIdx"] = 0
        chirpCfg["endIdx"] = 0
        chirpCfg["profileId"] = 0
        chirpCfg["startFreq"] = 0
        chirpCfg["freqSlopeVar"] = 0
        chirpCfg["idleTime"] = 0
        chirpCfg["adcStartTime"] = 0

        if (
            self.Input["platform"] == "Platform.xWR14xx"
            or self.Input["platform"] == "Platform.xWR18xx"
        ):
            if self.Input["Number_of_TX"] == 3:
                chirpCfg["txEnable"] = 1
            elif self.Input["Number_of_TX"] == 2:
                chirpCfg["txEnable"] = 1
            else:
                chirpCfg["txEnable"] = 1
        elif self.Input["platform"] == "Platform.xWR16xx":
            if self.Input["Number_of_TX"] == 2:
                chirpCfg["txEnable"] = 1
            else:
                chirpCfg["txEnable"] = 1
        else:
            chirpCfg["txEnable"] = 0

        chirpCfg = {}
        self.P["chirpCfg"].append(chirpCfg)
        chirpCfg["startIdx"] = 1
        chirpCfg["endIdx"] = 1
        chirpCfg["profileId"] = 0
        chirpCfg["startFreq"] = 0
        chirpCfg["freqSlopeVar"] = 0
        chirpCfg["idleTime"] = 0
        chirpCfg["adcStartTime"] = 0

        if (
            self.Input["platform"] == Platform.xWR14xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            if self.Input["Number_of_TX"] == 3:
                chirpCfg["txEnable"] = 4
            elif self.Input["Number_of_TX"] == 2:
                chirpCfg["txEnable"] = 4
            else:
                chirpCfg["txEnable"] = 0
        elif self.Input["platform"] == "Platform.xWR16xx":
            if self.Input["Number_of_TX"] == 2:
                chirpCfg["txEnable"] = 2
            else:
                chirpCfg["txEnable"] = 0
        else:
            chirpCfg["txEnable"] = 0

        if (
            self.Input["platform"] == Platform.xWR14xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["Number_of_TX"] == 3:
            # TODO 3D case
            chirpCfg = {}
            self.P["chirpCfg"].append(chirpCfg)
            chirpCfg["startIdx"] = 2
            chirpCfg["endIdx"] = 2
            chirpCfg["profileId"] = 0
            chirpCfg["startFreq"] = 0
            chirpCfg["freqSlopeVar"] = 0
            chirpCfg["idleTime"] = 0
            chirpCfg["adcStartTime"] = 0
            chirpCfg["txEnable"] = 2

        for idx in range(len(self.P["chirpCfg"])):
            chirpCfg = self.P["chirpCfg"][idx]
            self.P["lines"].append(" ")

    def generate_frameCfg(self):
        self.P["frameCfg"]["chirpStartIdx"] = 0
        self.P["frameCfg"]["chirpEndIdx"] = self.Input["Number_of_TX"] - 1
        self.P["frameCfg"]["numLoops"] = self.Input["Number_of_chirps"] // (
            self.P["frameCfg"]["chirpEndIdx"] - self.P["frameCfg"]["chirpStartIdx"] + 1
        )
        self.P["frameCfg"]["numFrames"] = 0
        self.P["frameCfg"]["framePeriodicity"] = self.Input["Frame_duration"]
        self.P["frameCfg"]["triggerSelect"] = 1
        self.P["frameCfg"]["frameTriggerDelay"] = 0
        self.P["lines"].append(
            " ".join(
                [
                    "frameCfg",
                    str(self.P["frameCfg"]["chirpStartIdx"]),
                    str(self.P["frameCfg"]["chirpEndIdx"]),
                    str(self.P["frameCfg"]["numLoops"]),
                    str(self.P["frameCfg"]["numFrames"]),
                    str(self.P["frameCfg"]["framePeriodicity"]),
                    str(self.P["frameCfg"]["triggerSelect"]),
                    str(self.P["frameCfg"]["frameTriggerDelay"]),
                ]
            )
        )

    def generate_guiMonitorCfg(self):
        self.P["guiMonitor"]["detectedObjects"] = (
            1 if templateObj.ti_widget_checkbox_scatter_plot.checked else 0
        )
        self.P["guiMonitor"]["logMagRange"] = (
            1 if templateObj.ti_widget_checkbox_range_profile.checked else 0
        )
        self.P["guiMonitor"]["noiseProfile"] = (
            1 if templateObj.ti_widget_checkbox_noise_profile.checked else 0
        )
        self.P["guiMonitor"]["rangeAzimuthHeatMap"] = (
            1 if templateObj.ti_widget_checkbox_azimuth_heatmap.checked else 0
        )
        self.P["guiMonitor"]["rangeDopplerHeatMap"] = (
            1 if templateObj.ti_widget_checkbox_doppler_heatmap.checked else 0
        )
        self.P["guiMonitor"]["statsInfo"] = (
            1 if templateObj.ti_widget_checkbox_statistics.checked else 0
        )
        if (
            self.Input["platform"] in [Platform.xWR16xx, Platform.xWR18xx]
            and self.Input["sdkVersionUint16"] >= 0x0101
        ):
            self.P["lines"].append(
                f'"guiMonitor -1" {self.P["guiMonitor"]["detectedObjects"]} {self.P["guiMonitor"]["logMagRange"]} {self.P["guiMonitor"]["noiseProfile"]} {self.P["guiMonitor"]["rangeAzimuthHeatMap"]} {self.P["guiMonitor"]["rangeDopplerHeatMap"]} {self.P["guiMonitor"]["statsInfo"]}'
            )
        else:
            self.P["lines"].append(
                f'"guiMonitor" {self.P["guiMonitor"]["detectedObjects"]} {self.P["guiMonitor"]["logMagRange"]} {self.P["guiMonitor"]["noiseProfile"]} {self.P["guiMonitor"]["rangeAzimuthHeatMap"]} {self.P["guiMonitor"]["rangeDopplerHeatMap"]} {self.P["guiMonitor"]["statsInfo"]}'
            )

    def generate_cfarCfg(self):
        cfarCfg = {}
        self.P["cfarRangeCfg"] = cfarCfg
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            cfarCfg["avgMode"] = 0
        else:
            cfarCfg["avgMode"] = 2
        cfarCfg["noiseAvgWindowLength"] = 8
        cfarCfg["guardLength"] = 4
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            cfarCfg["noiseSumDivisorAsShift"] = 4
        else:
            cfarCfg["noiseSumDivisorAsShift"] = 3
        cfarCfg["cyclicMode"] = 0
        cfarCfg["thresholdScale"] = self.convertSensitivitydBToLinear(
            self.Input["Range_Sensitivity"],
            self.Input["platform"],
            self.Input["Num_Virt_Ant"],
        )
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append(
                " ".join(
                    [
                        "cfarCfg -1 0",
                        str(cfarCfg["avgMode"]),
                        str(cfarCfg["noiseAvgWindowLength"]),
                        str(cfarCfg["guardLength"]),
                        str(cfarCfg["noiseSumDivisorAsShift"]),
                        str(cfarCfg["cyclicMode"]),
                        str(cfarCfg["thresholdScale"]),
                    ]
                )
            )
        else:
            self.P["lines"].append(
                " ".join(
                    [
                        "cfarCfg 0",
                        str(cfarCfg["avgMode"]),
                        str(cfarCfg["noiseAvgWindowLength"]),
                        str(cfarCfg["guardLength"]),
                        str(cfarCfg["noiseSumDivisorAsShift"]),
                        str(cfarCfg["cyclicMode"]),
                        str(cfarCfg["thresholdScale"]),
                    ]
                )
            )

        # CFAR doppler only supported in xWR16xx
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            cfarCfg = {}
            self.P["cfarDopplerCfg"] = cfarCfg
            cfarCfg["avgMode"] = 0
            # reduce the window and guard length for smaller FFT
            if self.Input["Doppler_FFT_size"] == 16:
                cfarCfg["noiseAvgWindowLength"] = 4
                cfarCfg["guardLength"] = 2
                cfarCfg["noiseSumDivisorAsShift"] = 3
            else:
                cfarCfg["noiseAvgWindowLength"] = 8
                cfarCfg["guardLength"] = 4
                cfarCfg["noiseSumDivisorAsShift"] = 4
            cfarCfg["cyclicMode"] = 0
            cfarCfg["thresholdScale"] = self.convertSensitivitydBToLinear(
                self.Input["Doppler_Sensitivity"],
                self.Input["platform"],
                self.Input["Num_Virt_Ant"],
            )
            if self.Input["sdkVersionUint16"] >= 0x0101:
                self.P["lines"].append(
                    " ".join(
                        [
                            "cfarCfg -1 1",
                            str(cfarCfg["avgMode"]),
                            str(cfarCfg["noiseAvgWindowLength"]),
                            str(cfarCfg["guardLength"]),
                            str(cfarCfg["noiseSumDivisorAsShift"]),
                            str(cfarCfg["cyclicMode"]),
                            str(cfarCfg["thresholdScale"]),
                        ]
                    )
                )
            else:
                self.P["lines"].append(
                    " ".join(
                        [
                            "cfarCfg 1",
                            str(cfarCfg["avgMode"]),
                            str(cfarCfg["noiseAvgWindowLength"]),
                            str(cfarCfg["guardLength"]),
                            str(cfarCfg["noiseSumDivisorAsShift"]),
                            str(cfarCfg["cyclicMode"]),
                            str(cfarCfg["thresholdScale"]),
                        ]
                    )
                )

    def generate_peakGroupingCfg(self):
        peakGrouping = {}
        peakGrouping["groupingMode"] = 1
        peakGrouping["rangeDimEn"] = (
            1 if templateObj.ti_widget_checkbox_grouppeak_rangedir.checked else 0
        )
        peakGrouping["dopplerDimEn"] = (
            1 if templateObj.ti_widget_checkbox_grouppeak_dopplerdir.checked else 0
        )
        peakGrouping["startRangeIdx"] = 1
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            peakGrouping["endRangeIdx"] = self.Input["Range_FFT_size"] - 1  # MMWSDK-546
        else:
            peakGrouping["endRangeIdx"] = (
                math.floor(0.9 * self.Input["Range_FFT_size"]) - 1
            )  # MMWSDK-546
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append(
                " ".join(
                    [
                        "peakGrouping -1",
                        str(peakGrouping["groupingMode"]),
                        str(peakGrouping["rangeDimEn"]),
                        str(peakGrouping["dopplerDimEn"]),
                        str(peakGrouping["startRangeIdx"]),
                        str(peakGrouping["endRangeIdx"]),
                    ]
                )
            )
        else:
            self.P["lines"].append(
                " ".join(
                    [
                        "peakGrouping",
                        str(peakGrouping["groupingMode"]),
                        str(peakGrouping["rangeDimEn"]),
                        str(peakGrouping["dopplerDimEn"]),
                        str(peakGrouping["startRangeIdx"]),
                        str(peakGrouping["endRangeIdx"]),
                    ]
                )
            )

    def generate_BFCfg(self):
        multiObjBeamForming = {}
        multiObjBeamForming["enabled"] = 1
        multiObjBeamForming["threshold"] = 0.5
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append(
                "multiObjBeamForming -1 "
                + str(multiObjBeamForming["enabled"])
                + " "
                + str(multiObjBeamForming["threshold"])
            )
        else:
            self.P["lines"].append(
                "multiObjBeamForming "
                + str(multiObjBeamForming["enabled"])
                + " "
                + str(multiObjBeamForming["threshold"])
            )

    def generate_clutterCfg(self):
        if self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["clutterRemoval"]["enabled"] = (
                1 if templateObj.ti_widget_checkbox_clutter_removal.checked else 0
            )
            if (
                self.Input["platform"] == Platform.xWR16xx
                or self.Input["platform"] == Platform.xWR18xx
            ):
                self.P["lines"].append(
                    "clutterRemoval -1 " + str(self.P["clutterRemoval"]["enabled"])
                )
            else:
                self.P["lines"].append(
                    "clutterRemoval " + str(self.P["clutterRemoval"]["enabled"])
                )

    def generate_DcRangeCfg(self):
        calibDcRangeSig = {}
        calibDcRangeSig["enabled"] = 0
        calibDcRangeSig["negativeBinIdx"] = -5
        calibDcRangeSig["positiveBinIdx"] = 8
        calibDcRangeSig["numAvgChirps"] = 256

        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append(
                " ".join(
                    [
                        "calibDcRangeSig",
                        "-1",
                        str(calibDcRangeSig["enabled"]),
                        str(calibDcRangeSig["negativeBinIdx"]),
                        str(calibDcRangeSig["positiveBinIdx"]),
                        str(calibDcRangeSig["numAvgChirps"]),
                    ]
                )
            )
        else:
            self.P["lines"].append(
                " ".join(
                    [
                        "calibDcRangeSig",
                        str(calibDcRangeSig["enabled"]),
                        str(calibDcRangeSig["negativeBinIdx"]),
                        str(calibDcRangeSig["positiveBinIdx"]),
                        str(calibDcRangeSig["numAvgChirps"]),
                    ]
                )
            )

    def generate_extendedVeloCfg(self):
        extendedMaxVelocity = {}
        extendedMaxVelocity["enabled"] = 0
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append(
                " ".join(
                    ["extendedMaxVelocity", "-1", str(extendedMaxVelocity["enabled"])]
                )
            )

    def generate_lowPowerCfg(self):
        lowPower = {}

        if (
            self.Input["platform"] == "xWR14xx"
            or self.Input["platform"] == "xWR16xx"
            or self.Input["platform"] == "xWR18xx"
        ) and self.Input["sdkVersionUint16"] >= 0x0200:
            lowPower["lpAdcMode"] = 1
        else:
            lowPower["lpAdcMode"] = 0

        self.P["lines"].append(" ".join(["lowPower 0", str(lowPower["lpAdcMode"])]))

    def generate_bpmCfg(self):
        bpmCfg = {}
        bpmCfg["enabled"] = 0
        bpmCfg["chirp0Idx"] = 0
        bpmCfg["chirp1Idx"] = 1
        if (
            self.Input["platform"] == "xWR16xx" or self.Input["platform"] == "xWR18xx"
        ) and self.Input["sdkVersionUint16"] >= 0x0102:
            self.P["lines"].append(
                " ".join(
                    [
                        "bpmCfg -1",
                        str(bpmCfg["enabled"]),
                        str(bpmCfg["chirp0Idx"]),
                        str(bpmCfg["chirp1Idx"]),
                    ]
                )
            )

    def generate_lvdsStreamCfg(self):
        lvdsStreamCfg = {}
        lvdsStreamCfg["isHeaderEnabled"] = 0
        lvdsStreamCfg["dataFmt"] = 0
        lvdsStreamCfg["isSwEnabled"] = 0

        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0102:
            self.P["lines"].append(
                "lvdsStreamCfg -1 "
                + str(lvdsStreamCfg["isHeaderEnabled"])
                + " "
                + str(lvdsStreamCfg["dataFmt"])
                + " "
                + str(lvdsStreamCfg["isSwEnabled"])
            )

    def generate_nearFieldCfg(self):
        nearFieldCfg = {}
        nearFieldCfg["enabled"] = 0
        nearFieldCfg["startRangeIdx"] = 0
        nearFieldCfg["endRangeIdx"] = 0
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ) and self.Input["sdkVersionUint16"] >= 0x0102:
            self.P["lines"].append(
                " ".join(
                    [
                        "nearFieldCfg -1",
                        str(nearFieldCfg["enabled"]),
                        str(nearFieldCfg["startRangeIdx"]),
                        str(nearFieldCfg["endRangeIdx"]),
                    ]
                )
            )

    def generate_compRangeBiasAndRxChanPhase(self):
        if self.Input["sdkVersionUint16"] >= 0x0101:
            if self.Input["platform"] == Platform.xWR16xx:
                self.P["lines"].append(
                    "compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0"
                )
            elif (
                self.Input["platform"] == Platform.xWR14xx
                or self.Input["platform"] == Platform.xWR18xx
            ):
                self.P["lines"].append(
                    "compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0"
                )

    def generate_measureRangeBiasAndRxChanPhase(self):
        if self.Input["sdkVersionUint16"] >= 0x0101:
            self.P["lines"].append("measureRangeBiasAndRxChanPhase 0 1.5 0.2")

    def generate_CQrxSat(self):
        CQrxSatMon = {}
        numPrimarySlices = 64
        primarySliceDuration = 4
        if self.Input["sdkVersionUint16"] >= 0x0102:
            samplingTime = (
                self.Input["Num_ADC_Samples"] / self.Input["ADC_Sampling_Rate"]
            )
            primarySliceDuration = math.ceil(samplingTime / 0.16 / 64)
            if primarySliceDuration < 4:
                primarySliceDuration = 4

            numPrimarySlices = math.ceil(samplingTime / (0.16 * primarySliceDuration))
            while numPrimarySlices > 64:
                primarySliceDuration += 1
                numPrimarySlices = math.ceil(
                    samplingTime / (0.16 * primarySliceDuration)
                )

            CQrxSatMon["profileIndx"] = self.P["profileCfg"]["profileId"]
            CQrxSatMon["satMonSel"] = 3
            CQrxSatMon["primarySliceDuration"] = primarySliceDuration
            CQrxSatMon["numSlices"] = numPrimarySlices * 2 - 1
            CQrxSatMon["rxChannelMask"] = 0

            self.P["lines"].append(
                f"CQRxSatMonitor {CQrxSatMon['profileIndx']} {CQrxSatMon['satMonSel']} {CQrxSatMon['primarySliceDuration']} {CQrxSatMon['numSlices']} {CQrxSatMon['rxChannelMask']}"
            )

    def generate_CQSigImg(self):
        CQSigImgMon = {}
        numPrimarySlices = 64
        samplePerPriSlice = 4
        if self.Input["sdkVersionUint16"] >= 0x0102:
            samplePerPriSlice = math.ceil(self.Input["Num_ADC_Samples"] / 64)
            if samplePerPriSlice < 4:
                samplePerPriSlice = 4
            if samplePerPriSlice % 2 != 0:
                samplePerPriSlice += 1

            numPrimarySlices = math.ceil(
                self.Input["Num_ADC_Samples"] / samplePerPriSlice
            )
            while numPrimarySlices > 64:
                samplePerPriSlice += 1
                numPrimarySlices = math.ceil(
                    self.Input["Num_ADC_Samples"] / samplePerPriSlice
                )

            CQSigImgMon["profileIndx"] = self.P["profileCfg"]["profileId"]
            CQSigImgMon["numSlices"] = numPrimarySlices * 2 - 1
            CQSigImgMon["timeSliceNumSamples"] = samplePerPriSlice

            self.P["lines"].append(
                f"CQSigImgMonitor {CQSigImgMon['profileIndx']} {CQSigImgMon['numSlices']} {CQSigImgMon['timeSliceNumSamples']}"
            )

    def generate_analogMon(self):
        analogMon = {}
        if self.Input["sdkVersionUint16"] >= 0x0102:
            analogMon["rxSatMonEn"] = 1
            analogMon["sigImgMonEn"] = 1
            self.P["lines"].append(
                f"analogMonitor {analogMon['rxSatMonEn']} {analogMon['sigImgMonEn']}"
            )

    def generateCfg(self):
        self.P["lines"].append(
            "% ***************************************************************"
        )
        self.P["lines"].append(
            f"% Created for SDK ver:{self.getVersionString(self.Input['sdkVersionUint16'])}"
        )
        self.P["lines"].append(f"% Created using Visualizer ver:{visualizerVersion}")
        self.P["lines"].append(f"% Frequency:{self.Input['Frequency_band']}")
        self.P["lines"].append(f"% Platform:{self.Input['platform']}")
        self.P["lines"].append(f"% Scene Classifier:{self.Input['subprofile_type']}")
        self.P["lines"].append(
            f"% Azimuth Resolution(deg):{self.Input['Azimuth_Resolution']}"
        )
        self.P["lines"].append(
            f"% Range Resolution(m):{self.Input['Range_Resolution']}"
        )
        self.P["lines"].append(
            f"% Maximum unambiguous Range(m):{self.Input['Maximum_range']}"
        )
        self.P["lines"].append(
            f"% Maximum Radial Velocity(m/s):{self.Input['Maximum_radial_velocity']}"
        )
        self.P["lines"].append(
            f"% Radial velocity resolution(m/s):{self.Input['Radial_velocity_Resolution']}"
        )
        self.P["lines"].append(f"% Frame Duration(msec):{self.Input['Frame_duration']}")
        self.P["lines"].append(
            f"% Range Detection Threshold (dB):{self.Input['Range_Sensitivity']}"
        )
        if (
            self.Input["platform"] == Platform.xWR16xx
            or self.Input["platform"] == Platform.xWR18xx
        ):
            self.P["lines"].append(
                f"% Doppler Detection Threshold (dB):{self.Input['Doppler_Sensitivity']}"
            )
        self.P["lines"].append(
            f"% Range Peak Grouping:{'enabled' if templateObj.ti_widget_checkbox_grouppeak_rangedir.checked else 'disabled'}"
        )
        self.P["lines"].append(
            f"% Doppler Peak Grouping:{'enabled' if templateObj.ti_widget_checkbox_grouppeak_dopplerdir.checked else 'disabled'}"
        )
        self.P["lines"].append(
            f"% Static clutter removal:{'enabled' if templateObj.ti_widget_checkbox_clutter_removal.checked else 'disabled'}"
        )
        self.P["lines"].append(
            "% ***************************************************************"
        )

        self.P["lines"].append("sensorStop")
        self.P["lines"].append("flushCfg")
        self.P["lines"].append("dfeDataOutputMode 1")

        self.generate_ChannelCfg()
        self.generate_adcCfg()
        self.generate_adcbufCfg()
        self.generate_profileCfg()
        self.generate_chirpCfg()
        self.generate_frameCfg()
        self.generate_lowPowerCfg()
        self.generate_guiMonitorCfg()
        self.generate_cfarCfg()
        self.generate_peakGroupingCfg()
        self.generate_BFCfg()
        self.generate_clutterCfg()
        self.generate_DcRangeCfg()
        self.generate_extendedVeloCfg()
        self.generate_bpmCfg()
        self.generate_lvdsStreamCfg()
        self.generate_nearFieldCfg()
        self.generate_compRangeBiasAndRxChanPhase()
        self.generate_measureRangeBiasAndRxChanPhase()
        self.generate_CQrxSat()
        self.generate_CQSigImg()
        self.generate_analogMon()
        self.P["lines"].append("sensorStart")
