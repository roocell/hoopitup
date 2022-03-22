import mpu6050 as mpu
import timer
import sys
from logger import log as log
import asyncio
import time

# don't have 6 pins to rim box so can't take advantage of MPU6050 INT pin.
# (who knows...the INT pin might not have been sufficient anyways)
# have to use an asynio timer instead to read MPY6050

print_motion_data = False # print every sample
print_partial_move = True # print a move halfway to our threshold

class Motion:
    def __init__(self, rim_done_moving):
        self.mpu_time = 0.025 # 25 ms
        self.mpu_samples = 0
        self.num_samples_for_avg = 4
        self.motion_acc = 0 # accumulator for avg
        self.motion_limit = 115 # % of stable (last reading to declare motion)

        self.motion = sys.maxsize # instantaneous motion
        self.motion_settling_time = 2 # seconds to determine miss
        self.motion_settling_time_race = 0.5 # to prevent race condition
        self.rim_done_moving = rim_done_moving

        mpu.MPU_Init()
        timer.Timer(self.mpu_time, self.mpu_timer, True)

    def rim_moved(self, current, last, change_per):
        log.debug("rim_moved time %.1f current %d last %d change_per %2.1f",
            time.monotonic(),
            current, last, change_per)

    async def mpu_timer(self, repeat, timeout):
        # sometimes we may get a bus error which results in an exception
        # we need to ignore this and continue taking samples
        try:
            # save power reading raw values
            acc_x = mpu.read_raw_data(mpu.ACCEL_XOUT_H)
            acc_y = mpu.read_raw_data(mpu.ACCEL_YOUT_H)
            acc_z = mpu.read_raw_data(mpu.ACCEL_ZOUT_H)
            gyro_x = mpu.read_raw_data(mpu.GYRO_XOUT_H)
            gyro_y = mpu.read_raw_data(mpu.GYRO_YOUT_H)
            gyro_z = mpu.read_raw_data(mpu.GYRO_ZOUT_H)
        except Exception as e:
            log.error(">>>>Error>>>> {} ".format(e))
            timer.Timer(self.mpu_time, self.mpu_timer, True)
            return

        # if values change by certain percentage, then decalre basket moved
        # but need to detect a change from stable state, then wait

        #motion = (abs(gyro_x) + abs(gyro_y) + abs(gyro_z))
        motion = (abs(acc_x) + abs(acc_y) + abs(acc_z))
        self.motion_acc += motion
        self.mpu_samples += 1

        if self.mpu_samples % self.num_samples_for_avg == 0:
            motion = self.motion_acc / self.num_samples_for_avg
            self.motion_acc = 0
        else:
            # take more samples before evaluating
            timer.Timer(self.mpu_time, self.mpu_timer, True)
            return

        # TODO: will need something smarter than this after experimenting on real hoop
        movement_detected = False
        if motion > (self.motion * self.motion_limit / 100):
            movement_detected = True
            self.rim_moved(motion, self.motion, (motion * 100 / self.motion))

        print = False
        if print_motion_data == True or movement_detected:
            print = True
        partial_limit = abs(self.motion_limit-100)/2 + 100
        if print_partial_move and motion > (self.motion * partial_limit / 100):
            print = True

        if print:
            change_per = 0
            if self.motion > 0:
                change_per = (motion * 100 / self.motion)

            log.debug("ax %4d\t ay %6d\t az %3d\t gx %4d\t gy %4d\t gz %4d\t "
                "m %d\t self.m %d per %2.1f",
                acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, motion, self.motion, change_per
            )
        self.motion = motion


        if repeat:
            if movement_detected:
                donetimer = timer.Timer(self.motion_settling_time, self.rim_done_moving, False)
                # easy debounce - don't look at MPU again until after settling time
                timer.Timer(self.motion_settling_time, self.mpu_timer, True)
            else:
                timer.Timer(self.mpu_time, self.mpu_timer, True)
