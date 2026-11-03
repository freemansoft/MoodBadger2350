# Simulator stand-in for the PCF85063A real-time clock driver.
# Time comes from the host clock; alarms and timers never fire.

import time


class PCF85063A:
    def __init__(self, i2c=None):
        pass

    def datetime(self, dt=None):
        if dt is not None:
            return None
        year, month, day, hour, minute, second, weekday = time.localtime()[:7]
        return year, month, day, hour, minute, second, weekday

    def enable_alarm_interrupt(self, enable):
        pass

    def enable_timer_interrupt(self, enable, flag_only=False):
        pass

    def clear_alarm_flag(self):
        pass

    def clear_timer_flag(self):
        pass

    def read_alarm_flag(self):
        return False

    def read_timer_flag(self):
        return False

    def set_alarm(self, *args):
        pass

    def unset_alarm(self):
        pass

    def set_timer(self, *args):
        pass
